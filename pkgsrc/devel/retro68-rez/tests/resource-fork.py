#!/usr/bin/env python3
"""Exercise the real Rez CLI on Darwin named forks using a caller-selected executable."""
import argparse
import ctypes
import hashlib
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rez', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--fixture', type=Path, help='use the bytes of an existing Mach-O or ordinary file')
args = parser.parse_args()
if sys.platform != 'darwin':
    raise SystemExit('named resource forks require Darwin')

libc = ctypes.CDLL(None, use_errno=True)
libc.getxattr.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                          ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int)
libc.getxattr.restype = ctypes.c_ssize_t
libc.setxattr.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                          ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int)
libc.setxattr.restype = ctypes.c_int
def getxattr(path, name):
    path, name = os.fsencode(path), name.encode()
    length = libc.getxattr(path, name, None, 0, 0, 0)
    if length < 0:
        raise OSError(ctypes.get_errno(), 'getxattr size')
    buf = ctypes.create_string_buffer(length)
    if libc.getxattr(path, name, buf, length, 0, 0) != length:
        raise OSError(ctypes.get_errno(), 'getxattr')
    return buf.raw
def setxattr(path, name, value):
    buf = ctypes.create_string_buffer(value)
    if libc.setxattr(os.fsencode(path), name.encode(), buf, len(value), 0, 0):
        raise OSError(ctypes.get_errno(), 'setxattr')

with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    root = Path(directory)
    target = root / 'fixture'
    target.write_bytes(args.fixture.read_bytes() if args.fixture else b'ordinary data fork\0' * 128)
    target.chmod(0o751)
    finder = b'TESTCRTR' + bytes(range(24))
    setxattr(target, 'com.apple.FinderInfo', finder)
    setxattr(target, 'org.emberbsd.test', b'preserve attribute')
    first = root / 'first.rsrc'
    first.write_text("data 'TEST' (1) { $\"0102030405060708\" };\ndata 'KEEP' (2, \"keep\", purgeable) { $\"CAFE\" };\n")
    second = root / 'second.rsrc'
    second.write_text("data 'TEST' (1) { $\"0304\" };\n")
    def run(*words, ok=True):
        p = subprocess.run([str(args.rez), *map(str, words)], capture_output=True)
        assert (p.returncode == 0) == ok, (p.returncode, p.stderr.decode(errors='replace'))
    def metadata():
        return (hashlib.sha256(target.read_bytes()).digest(), target.stat().st_mode,
                getxattr(target, 'com.apple.FinderInfo'), getxattr(target, 'org.emberbsd.test'))
    def resources(blob):
        u16 = lambda off: struct.unpack_from('>H', blob, off)[0]
        u32 = lambda off: struct.unpack_from('>I', blob, off)[0]
        data, mapping = u32(0), u32(4)
        types = mapping + u16(mapping + 24)
        names = mapping + u16(mapping + 26)
        found = {}
        for i in range((u16(types) + 1) & 0xffff):
            entry = types + 2 + 8*i
            kind = blob[entry:entry+4]
            refs = types + u16(entry+6)
            for j in range(u16(entry+4)+1):
                ref = refs + 12*j
                ident = struct.unpack_from('>h', blob, ref)[0]
                info, name_offset = u32(ref+4), u16(ref+2)
                start = data + (info & 0xffffff)
                name = b'' if name_offset == 0xffff else blob[names+name_offset+1:names+name_offset+1+blob[names+name_offset]]
                found[kind, ident] = (blob[start+4:start+4+u32(start)], name, info >> 24)
        return found
    before = metadata()
    run('--input-format=text', '--resource-fork-only', '--append', '-o', target, first)
    first_fork = getxattr(target, 'com.apple.ResourceFork')
    assert resources(first_fork) == {(b'TEST', 1): (bytes(range(1, 9)), b'', 0), (b'KEEP', 2): (b'\xca\xfe', b'keep', 32)}
    assert metadata() == before
    binary = root / 'copy.as'
    run('--input-format=text', '-o', binary, first)
    run('--input-format=binary', '--resource-fork-only', '--append', '-o', target, binary)
    assert resources(getxattr(target, 'com.apple.ResourceFork')) == resources(first_fork)
    assert metadata() == before
    run('--input-format=text', '--resource-fork-only', '--append', '-o', target, second)
    second_fork = getxattr(target, 'com.apple.ResourceFork')
    assert resources(second_fork) == {(b'TEST', 1): (b'\x03\x04', b'', 0), (b'KEEP', 2): (b'\xca\xfe', b'keep', 32)}
    assert len(second_fork) == len(first_fork) - 6
    assert metadata() == before
    bad = root / 'bad.rsrc'
    bad.write_text("data 'TEST' (1) { $\"broken\" ")
    run('--input-format=text', '--resource-fork-only', '--append', '-o', target, bad, ok=False)
    assert getxattr(target, 'com.apple.ResourceFork') == second_fork and metadata() == before
    invalid_binary = root / 'invalid.as'
    invalid_binary.write_bytes(b'not an AppleSingle resource')
    run('--input-format=binary', '--resource-fork-only', '--append', '-o', target, invalid_binary, ok=False)
    assert getxattr(target, 'com.apple.ResourceFork') == second_fork and metadata() == before
    # Valid AppleSingle header with a truncated resource-fork entry.
    invalid_binary.write_bytes(struct.pack('>II16sHIII', 0x51600, 0x20000, b'', 1, 2, 38, 16) + b'bad')
    run('--input-format=binary', '--resource-fork-only', '--append', '-o', target, invalid_binary, ok=False)
    assert getxattr(target, 'com.apple.ResourceFork') == second_fork and metadata() == before
    with open(str(target) + '/..namedfork/rsrc', 'wb') as fork:
        fork.write(b'malformed')
    run('--input-format=text', '--resource-fork-only', '--append', '-o', target, second, ok=False)
    assert getxattr(target, 'com.apple.ResourceFork') == b'malformed' and metadata() == before
    with open(str(target) + '/..namedfork/rsrc', 'wb') as fork:
        fork.write(second_fork)
    target.chmod(0o400)
    readonly = metadata()
    run('--input-format=text', '--resource-fork-only', '--append', '-o', target, second, ok=False)
    assert getxattr(target, 'com.apple.ResourceFork') == second_fork and metadata() == readonly
print('Rez named fork preservation and failure checks: PASS')
