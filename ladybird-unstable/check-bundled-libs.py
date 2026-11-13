#!/usr/bin/env python3
"""Fail the build when a bundled library's PT_DYNAMIC disagrees with its PT_LOAD.

vcpkg's rpath rewrite (patchelf) rewrites the whole ELF and can leave the
program-header table out of step, which ld.so then reads as an empty dynamic
section. dlopen does not catch that, so this reads the headers directly.
"""

import glob
import os
import struct
import sys

LOAD = 1
DYNAMIC = 2
PHDR_SIZE = 56


def damage(path):
    data = open(path, "rb").read()
    if data[:4] != b"\x7fELF" or data[4] != 2:
        return "not ELF64"
    phoff, = struct.unpack_from("<Q", data, 0x20)
    phentsize, = struct.unpack_from("<H", data, 0x36)
    phnum, = struct.unpack_from("<H", data, 0x38)
    if phoff + phentsize * phnum > len(data):
        return "program header table runs past EOF"
    loads = []
    dynamic = None
    for index in range(phnum):
        offset = phoff + index * phentsize
        if offset + PHDR_SIZE > len(data):
            return "program header %d runs past EOF" % index
        kind, _flags, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _align = struct.unpack_from(
            "<IIQQQQQQ", data, offset)
        if kind == LOAD:
            loads.append((p_offset, p_vaddr, p_filesz))
        elif kind == DYNAMIC:
            dynamic = (p_offset, p_vaddr)
    if dynamic is None:
        return "no PT_DYNAMIC"
    dyn_offset, dyn_vaddr = dynamic
    hosts = [load for load in loads if load[1] <= dyn_vaddr < load[1] + load[2]]
    if not hosts:
        return "PT_DYNAMIC is outside every PT_LOAD"
    load_offset, load_vaddr, _size = hosts[0]
    drift = (dyn_offset - load_offset) - (dyn_vaddr - load_vaddr)
    if drift:
        return "PT_DYNAMIC is %#x off from its PT_LOAD" % drift
    if dyn_offset + 8 > len(data):
        return "PT_DYNAMIC runs past EOF"
    if struct.unpack_from("<q", data, dyn_offset)[0] == 0:
        return "ld.so reads DT_NULL where the dynamic section starts"
    return None


def main():
    libdir = sys.argv[1]
    objects = [path for path in sorted(glob.glob(os.path.join(libdir, "*.so*")))
               if not os.path.islink(path) and os.path.isfile(path)]
    damaged = 0
    for path in objects:
        why = damage(path)
        if why:
            print("FATAL: %s: %s" % (path, why), file=sys.stderr)
            damaged += 1
    print("bundled libraries: %d checked, %d damaged" % (len(objects), damaged))
    return 1 if damaged else 0


if __name__ == "__main__":
    sys.exit(main())
