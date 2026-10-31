# SPDX-License-Identifier: BSD-2-Clause
"""Shared arguments and selected native tools for U-Boot source checks."""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if not __debug__:
    raise SystemExit('Run these checks without Python optimization (-O)')


def arguments(description, configure=None, *, compiler=True):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--source', type=Path, required=True,
                        help='prepared U-Boot source directory')
    parser.add_argument('--host-prefix', type=Path, required=True,
                        help='native Ports prefix containing clang and libfdt')
    if configure is not None:
        configure(parser)
    args = parser.parse_args()
    args.source = args.source.resolve(strict=True)
    args.host_prefix = args.host_prefix.resolve(strict=True)
    if compiler:
        args.clang = (args.host_prefix / 'bin/clang').resolve(strict=True)
        if not args.clang.is_relative_to(args.host_prefix):
            parser.error('clang resolves outside the selected host prefix')
        linker_name = 'ld64.lld' if sys.platform == 'darwin' else 'ld.lld'
        linker = (args.host_prefix / 'bin' / linker_name).resolve(strict=True)
        if not linker.is_relative_to(args.host_prefix):
            parser.error('lld resolves outside the selected host prefix')
    return args


def compile_and_run(args, source, *, include=(), libraries=(), cflags=(), run_args=()):
    with tempfile.TemporaryDirectory(prefix='uboot-source-test-') as directory:
        work = Path(directory)
        cfile, exe = work / 'test.c', work / 'test'
        cfile.write_text(source)
        cmd = [str(args.clang), '-fuse-ld=lld', '-O1', '-g',
               '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
               '-fno-omit-frame-pointer',
               *cflags, *(f'-I{p}' for p in include), str(cfile),
               f'-L{args.host_prefix / "lib"}',
               f'-Wl,-rpath,{args.host_prefix / "lib"}',
               *(f'-l{x}' for x in libraries), '-o', str(exe)]
        env = dict(os.environ)
        env['PATH'] = os.pathsep.join((str(args.host_prefix / 'bin'),
                                      str(args.host_prefix / 'gnu/bin')))
        subprocess.run(cmd, check=True, env=env)
        subprocess.run([str(exe), *(str(x) for x in run_args)], check=True, env=env)
