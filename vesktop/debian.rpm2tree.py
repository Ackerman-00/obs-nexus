#!/usr/bin/env python3
"""Extract the installed payload tree from an RPM file using stdlib only.

Usage: python3 rpm2tree.py <package.rpm> <destdir>

Parses the RPM lead + signature/main headers (with padding scan, like the
spec %prep python does for ar), decompresses the payload (gzip/xz/bzip2 via
stdlib) and unpacks cpio newc entries into destdir, preserving modes.
Also unpacks the stripped "07070X" payload variant rpm writes for files
larger than 4 GiB and for v6 packages: those headers carry only the file
index, so names/sizes/modes come from the main header tags.

Used by the nexus repack recipes (fluxer, vesktop) in two places:
  * update.sh (CI): verify a downloaded upstream RPM is extractable.
  * debian/rules (Debian build): materialize the payload tree without any
    rpm tooling in the buildroot (Debian has no guaranteed rpm2cpio).

Keep the per-package `debian.rpm2tree.py` copies in sync with this file.
Pure stdlib, no third-party modules.
"""
import bz2
import gzip
import lzma
import struct
import sys
from pathlib import Path

TAG_FILESIZES = 1028
TAG_FILEMODES = 1030
TAG_DIRINDEXES = 1116
TAG_BASENAMES = 1117
TAG_DIRNAMES = 1118
TAG_PAYLOADCOMPRESSOR = 1125
TAG_LONGFILESIZES = 5008

CPIO_STRIPPED_MAGIC = b'07070X'
CPIO_NEWC_MAGIC = b'070701'
CPIO_CRC_MAGIC = b'070702'


def _header(d, pos):
    """Parse one header at pos; return (entries, data_start, end) or None."""
    if d[pos:pos + 3] != b'\x8e\xad\xe8':
        return None
    n = int.from_bytes(d[pos + 8:pos + 12], 'big')
    dlen = int.from_bytes(d[pos + 12:pos + 16], 'big')
    entries = {}
    for i in range(n):
        tag, typ, off, cnt = struct.unpack(
            '>IIII', d[pos + 16 + i * 16:pos + 32 + i * 16])
        entries[tag] = (typ, off, cnt)
    start = pos + 16 + n * 16
    return entries, start, start + dlen


def _ints(d, entries, start, tag, width):
    typ, off, cnt = entries[tag]
    return [int.from_bytes(d[start + off + i * width:start + off + (i + 1) * width], 'big')
            for i in range(cnt)]


def _strings(d, entries, start, tag):
    typ, off, cnt = entries[tag]
    if typ == 6:
        end = d.find(b'\0', start + off)
        return [d[start + off:end].decode(errors='ignore')]
    limit = min([o for (t, o, c) in entries.values() if o > off] or [off + cnt])
    raw = d[start + off:start + limit]
    return [s.decode(errors='ignore') for s in raw.split(b'\0') if s][:cnt]


def file_table(d, entries, start):
    """Rebuild (path, size, mode) per payload index from the header tags."""
    dirs = _strings(d, entries, start, TAG_DIRNAMES)
    bases = _strings(d, entries, start, TAG_BASENAMES)
    diridx = _ints(d, entries, start, TAG_DIRINDEXES, 4)
    modes = _ints(d, entries, start, TAG_FILEMODES, 2)
    if TAG_LONGFILESIZES in entries:
        sizes = _ints(d, entries, start, TAG_LONGFILESIZES, 8)
    else:
        sizes = _ints(d, entries, start, TAG_FILESIZES, 4)
    return [(dirs[diridx[i]] + bases[i], sizes[i], modes[i])
            for i in range(len(bases))]


def rpm_payload(path):
    """Return (payload_bytes, compressor, files) for an RPM file."""
    d = Path(path).read_bytes()
    if d[:4] != b'\xed\xab\xee\xdb':
        raise ValueError('%s: not an RPM (bad lead magic)' % path)
    sig = _header(d, 96)
    if sig is None:
        raise ValueError('%s: signature header unreadable' % path)
    pos = sig[2]
    for _ in range(64):
        main = _header(d, pos)
        if main is not None:
            break
        pos += 1
    else:
        raise ValueError('%s: main header not found' % path)
    entries, start, end = main
    compressor = 'gzip'
    if TAG_PAYLOADCOMPRESSOR in entries:
        compressor = _strings(d, entries, start, TAG_PAYLOADCOMPRESSOR)[0]
    files = []
    if all(t in entries for t in (TAG_DIRNAMES, TAG_BASENAMES, TAG_DIRINDEXES,
                                  TAG_FILEMODES)):
        files = file_table(d, entries, start)
    return d[end:], compressor, files


def decompress(payload, compressor):
    if compressor == 'xz':
        return lzma.decompress(payload)
    if compressor == 'gzip':
        return gzip.decompress(payload)
    if compressor in ('bzip2', 'bz2'):
        return bz2.decompress(payload)
    raise ValueError('unsupported payload compressor: %r' % compressor)


def _write(dest, name, mode, data):
    target = dest / name
    if not name or '..' in Path(name).parts:
        return 0
    if mode & 0o170000 == 0o040000:
        target.mkdir(parents=True, exist_ok=True)
        return 1
    if mode & 0o170000 == 0o120000:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() or target.exists():
            target.unlink()
        target.symlink_to(data.decode(errors='ignore'))
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.chmod(mode & 0o7777)
    return 1


def cpio_extract(raw, dest, files):
    """Unpack cpio newc (070701) and stripped (07070X) payloads."""
    dest = Path(dest)
    pos, count = 0, 0
    while pos + 110 <= len(raw):
        if raw[pos:pos + 6] == CPIO_STRIPPED_MAGIC:
            idx = int(raw[pos + 6:pos + 14], 16)
            if idx == 0xFFFFFFFF:
                break
            count += _write(dest, files[idx][0].lstrip('/'), files[idx][2],
                            raw[pos + 16:pos + 16 + files[idx][1]])
            size = files[idx][1]
            pos += 16 + size + (-size) % 4
            continue
        if raw[pos:pos + 6] not in (CPIO_NEWC_MAGIC, CPIO_CRC_MAGIC):
            break
        mode = int(raw[pos + 14:pos + 22], 16)
        filesz = int(raw[pos + 54:pos + 62], 16)
        namesz = int(raw[pos + 94:pos + 102], 16)
        name = raw[pos + 110:pos + 110 + namesz].rstrip(b'\0').decode()
        dataoff = pos + 110 + namesz
        dataoff += (-dataoff) % 4
        if name == 'TRAILER!!!':
            break
        count += _write(dest, name.lstrip('/'), mode, raw[dataoff:dataoff + filesz])
        pos = dataoff + filesz + (-filesz) % 4
    return count



def main():
    if len(sys.argv) != 3:
        print('usage: rpm2tree.py <package.rpm> <destdir>', file=sys.stderr)
        return 2
    payload, compressor, files = rpm_payload(sys.argv[1])
    count = cpio_extract(decompress(payload, compressor), sys.argv[2], files)
    if count == 0:
        print('rpm2tree: no payload members extracted', file=sys.stderr)
        return 1
    if files and count < len(files):
        print('rpm2tree: payload truncated: %d of %d header entries'
              % (count, len(files)), file=sys.stderr)
        return 1
    print('rpm2tree: %d members -> %s' % (count, sys.argv[2]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
