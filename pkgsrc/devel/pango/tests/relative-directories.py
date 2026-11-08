#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the native Pango directory getter ABI from a relocated shared library.

Only a temporary library copy is written. Dependencies may still load from the
original native prefix; this checks Pango defaults, not full SDK qualification.
Run with the Ports library, whose configured libdir/sysconfdir are lib/etc.
"""
import argparse
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def worker(library, mode):
    root = library.parent.parent
    names = ('PANGO_SYSCONFDIR', 'PANGO_LIBDIR')
    overrides = {}
    expected = [str(root / 'etc/pango'), str(root / 'lib/pango')]
    for index, name in enumerate(names):
        if mode in ('overrides', 'empty') or mode == name:
            value = '' if mode == 'empty' else str(root / ('override-' + name))
            overrides[name] = value
            expected[index] = str(Path(value) / 'pango')

    lib = ctypes.CDLL(str(library))
    functions = (lib.pango_get_sysconf_subdirectory, lib.pango_get_lib_subdirectory)
    for function, value in zip(functions, expected):
        for name in names:
            os.environ.pop(name, None)
        os.environ.update(overrides)
        function.argtypes = []
        function.restype = ctypes.c_void_p
        pointer = function()
        assert pointer, function.__name__ + ' returned NULL'
        actual = os.fsdecode(ctypes.string_at(pointer))
        assert actual == value, (function.__name__, actual, value)
        for name in names:
            os.environ[name] = str(root / 'later-change')
        # Transfer-none strings and the first-call result remain stable.
        assert function() == pointer, function.__name__ + ' changed its cached pointer'
        assert os.fsdecode(ctypes.string_at(pointer)) == value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library', type=Path)
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.library, args.worker)
        return
    library = args.library.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='pango-directories-') as temporary:
        root = Path(temporary).resolve() / 'moved λ & prefix'
        (root / 'lib').mkdir(parents=True)
        copied = root / 'lib' / library.name
        shutil.copy2(library, copied)
        # etc/pango and lib/pango deliberately do not exist: getters report
        # paths and must not fall back to a producer directory on absence.
        for mode in ('defaults', 'overrides', 'empty', 'PANGO_SYSCONFDIR', 'PANGO_LIBDIR'):
            subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()),
                            str(copied), '--worker', mode], check=True)
    print('PASS: relocated defaults, independent overrides, empty values, cached pointers')


if __name__ == '__main__':
    main()
