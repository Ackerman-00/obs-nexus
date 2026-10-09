#!/usr/bin/env python3
# Copy of tools/rpm2tree.py at the pinned repo revision below.
# Keep in sync: any fix here belongs in tools/rpm2tree.py first.
"""Extract the installed payload tree from an RPM file using stdlib only.

Usage: python3 rpm2tree.py <package.rpm> <destdir>

Parses the RPM lead + signature/main headers (with padding scan, like the
spec %prep python does for ar), decompresses the payload (gzip/xz/bzip2 via
stdlib) and unpacks cpio newc entries into destdir, preserving modes.

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


def rpm_payload(path):
    """Return (payload_bytes, compressor_name) for an RPM file."""
    d = Path(path).read_bytes()
    if d[:4] != b'\xed\xab\xee\xdb':
        raise ValueError('%s: not an RPM (bad lead magic)' % path)

    def parse_header(pos):
        if d[pos:pos + 3] != b'\x8e\xad\xe8':
            return None, pos
        n = int.from_bytes(d[pos + 8:pos + 12], 'big')
        dlen = int.from_bytes(d[pos + 12:pos + 16], 'big')
        entries = [struct.unpack('>IIII', d[pos + 16 + i * 16:pos + 32 + i * 16])
                   for i in range(n)]
        base = pos + 16 + n * 16
        tags = {}
        for tag, typ, off, _ in entries:
            if typ in (6, 8, 9):  # string / string-array types
                end = d.find(b'\x00', base + off)
                tags[tag] = d[base + off:end].decode(errors='ignore')
        return tags, base + dlen

    _, pos = parse_header(96)
    if pos is None:
        raise ValueError('%s: signature header unreadable' % path)
    for _ in range(64):  # padding may sit between the two headers
        tags, pos2 = parse_header(pos)
        if tags is not None:
            pos = pos2
            break
        pos += 1
    else:
        raise ValueError('%s: main header not found' % path)
    return d[pos:], tags.get(1125, 'gzip')


def decompress(payload, compressor):
    if compressor == 'xz':
        return lzma.decompress(payload)
    if compressor == 'gzip':
        return gzip.decompress(payload)
    if compressor in ('bzip2', 'bz2'):
        return bz2.decompress(payload)
    raise ValueError('unsupported payload compressor: %r' % compressor)


def cpio_extract(raw, dest):
    """Unpack cpio newc (070701) entries. Returns member count."""
    dest = Path(dest)
    pos, count = 0, 0
    while pos + 110 <= len(raw):
        if raw[pos:pos + 6] != b'070701':
            break
        mode = int(raw[pos + 14:pos + 22], 16)
        filesz = int(raw[pos + 54:pos + 62], 16)
        namesz = int(raw[pos + 94:pos + 102], 16)
        name = raw[pos + 110:pos + 110 + namesz].rstrip(b'\0').decode()
        dataoff = pos + 110 + namesz
        dataoff += (-dataoff) % 4
        if name == 'TRAILER!!!':
            break
        target = dest / name
        if mode & 0o040000:
            target.mkdir(parents=True, exist_ok=True)
        elif name not in ('.',):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw[dataoff:dataoff + filesz])
            target.chmod(mode & 0o7777)
        count += 1
        pos = dataoff + filesz + (-filesz) % 4
    return count


def main():
    if len(sys.argv) != 3:
        print('usage: rpm2tree.py <package.rpm> <destdir>', file=sys.stderr)
        return 2
    payload, compressor = rpm_payload(sys.argv[1])
    count = cpio_extract(decompress(payload, compressor), sys.argv[2])
    if count == 0:
        print('rpm2tree: no payload members extracted', file=sys.stderr)
        return 1
    print('rpm2tree: %d members -> %s' % (count, sys.argv[2]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
