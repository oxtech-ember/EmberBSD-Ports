#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the actual native libnetpbm at a different prefix; no compilation.

Pass the built shared library. Only a temporary copy and test dictionaries are
written. Dependencies may still load from the supplied build's native prefix;
this tests dictionary lookup, not complete SDK relocation qualification.
"""
import argparse
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def worker(library):
    lib = ctypes.CDLL(str(library))
    lib.pm_openColornameFile.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.pm_openColornameFile.restype = ctypes.c_void_p
    libc = ctypes.CDLL(None)
    libc.fileno.argtypes = [ctypes.c_void_p]
    libc.fileno.restype = ctypes.c_int
    libc.fclose.argtypes = [ctypes.c_void_p]
    libc.fclose.restype = ctypes.c_int

    def read(filename=None):
        stream = lib.pm_openColornameFile(os.fsencode(filename) if filename else None, 0)
        if not stream:
            return None
        try:
            return os.read(libc.fileno(stream), 4096)
        finally:
            libc.fclose(stream)

    root = library.parent.parent
    dictionary = root / 'share/netpbm/rgb.txt'
    explicit = root / 'explicit.txt'
    explicit.write_bytes(b'4 5 6 explicit-test\n')
    override = root / 'override.txt'
    override.write_bytes(b'7 8 9 environment-test\n')
    os.environ.pop('RGBDEF', None)
    actual = read()
    if actual != dictionary.read_bytes():
        raise AssertionError('default lookup did not use the relocated library dictionary')
    os.environ['RGBDEF'] = str(override)
    assert read() == override.read_bytes(), 'RGBDEF override was ignored'
    assert read(explicit) == explicit.read_bytes(), 'explicit filename must precede RGBDEF'
    os.environ['RGBDEF'] = str(root / 'missing-override')
    assert read() is None, 'missing explicit RGBDEF must not fall back'
    os.environ.pop('RGBDEF')
    dictionary.unlink()
    assert read() is None, 'missing relocated data must not fall back to producer/system data'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library', type=Path)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.library)
        return
    library = args.library.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='netpbm-rgb-') as temporary:
        root = Path(temporary)
        (root / 'lib').mkdir()
        (root / 'share/netpbm').mkdir(parents=True)
        copied = root / 'lib' / library.name
        shutil.copy2(library, copied)
        (root / 'share/netpbm/rgb.txt').write_bytes(b'1 2 3 relocated-test\n')
        subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()),
                        str(copied), '--worker'], check=True)
    print('PASS: relative dictionary, explicit/environment overrides, missing-file refusal')


if __name__ == '__main__':
    main()
