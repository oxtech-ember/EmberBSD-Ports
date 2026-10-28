#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the versioned uvwasi shared library with a real consumer.

The recipe patches are applied to the distfile, and the library is built
and staged with the native Ports tools. The staged library must have the
API-major name (libuvwasi.0.dylib on Darwin), and consumer.c must link to
that name, not to the unversioned linker name, and run. The cross recipe
must list the versioned target names libuvwasi.so.0 and
libuvwasi.so.<version> in its PLIST.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

sys.dont_write_bytecode = True
VERSION = '0.0.23'
PKGPATH = 'devel/uvwasi'


def run(*command, **options):
    return subprocess.run([str(part) for part in command], check=True, capture_output=True, text=True, **options)


def stage(archive, pkgsrc, prefix, work):
    """Build the patched library and return the staged prefix."""
    with tarfile.open(archive) as tar:
        tar.extractall(work / 'source', filter='data')
    source = work / 'source' / ('uvwasi-' + VERSION)
    for patch in sorted((pkgsrc / PKGPATH / 'patches').glob('patch-*')):
        with patch.open() as stream:
            run(prefix / 'bin/nbpatch', '-p0', '-s', '-N', '-d', source, stdin=stream)
    build = work / 'build'
    run(prefix / 'bin/cmake', '-S', source, '-B', build, '-G', 'Ninja',
        '-DCMAKE_MAKE_PROGRAM=' + str(prefix / 'bin/ninja'), '-DCMAKE_C_COMPILER=' + str(prefix / 'bin/clang'),
        '-DCMAKE_PREFIX_PATH=' + str(prefix), '-DCMAKE_INSTALL_PREFIX=/usr/pkg', '-DBUILD_TESTING=OFF',
        env=dict(os.environ, LDFLAGS='-L' + str(prefix / 'lib')))  # The recipe links libuv by name.
    run(prefix / 'bin/cmake', '--build', build)
    run(prefix / 'bin/cmake', '--install', build, env=dict(os.environ, DESTDIR=str(work / 'stage')))
    return work / 'stage/usr/pkg'


def native(archive, pkgsrc, prefix, work):
    if sys.platform != 'darwin':
        return 'the native check supports only a Darwin build host'
    staged = stage(archive, pkgsrc, prefix, work)
    lib = staged / 'lib'
    soname = 'libuvwasi.0.dylib'
    for name in ('libuvwasi.dylib', soname, 'libuvwasi.' + VERSION + '.dylib'):
        if not (lib / name).exists():
            return 'no staged lib/' + name + '; staged: ' + ' '.join(sorted(p.name for p in lib.glob('libuvwasi*')))
    identity = run(prefix / 'bin/llvm-objdump', '--macho', '--dylib-id', lib / 'libuvwasi.dylib').stdout
    if not identity.rstrip().endswith('/' + soname):
        return 'the library identity is not ' + soname + ': ' + identity.strip()
    consumer = work / 'consumer'
    run(prefix / 'bin/clang', Path(__file__).with_name('consumer.c'), '-I', staged / 'include',
        '-I', prefix / 'include', '-L', lib, '-luvwasi', '-Wl,-rpath,' + str(lib), '-Wl,-rpath,' + str(prefix / 'lib'),
        '-o', consumer)
    used = run(prefix / 'bin/llvm-objdump', '--macho', '--dylibs-used', consumer).stdout
    if '/' + soname + ' ' not in used:
        return 'the consumer does not link to ' + soname + ': ' + used.strip()
    result = subprocess.run([str(consumer)], capture_output=True, text=True)
    if result.returncode != 0:
        return 'the consumer fails with exit ' + str(result.returncode)
    return None


def cross(tool, makeconf, pkgsrc):
    result = subprocess.run([str(tool), '-V', '${PLIST_SUBST}'], cwd=pkgsrc / PKGPATH, capture_output=True,
                            text=True, env=dict(os.environ, MAKECONF=str(makeconf)))
    if result.returncode != 0:
        return 'cannot evaluate the cross recipe: ' + result.stderr.strip()[:300]
    values = dict(word.split('=', 1) for word in result.stdout.split() if '=' in word)
    expected = {'UVWASI_SHARED': 'libuvwasi.so', 'UVWASI_SONAME': 'libuvwasi.so.0',
                'UVWASI_VERSIONED': 'libuvwasi.so.' + VERSION}
    plist = (pkgsrc / PKGPATH / 'PLIST').read_text().splitlines()
    for variable, name in expected.items():
        if values.get(variable) != name:
            return 'cross ' + variable + ' is ' + repr(values.get(variable)) + ', not ' + name
        if 'lib/${' + variable + '}' not in plist:
            return 'the PLIST does not list lib/' + name
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distfile', type=Path, required=True, help='uvwasi-' + VERSION + '.tar.gz')
    parser.add_argument('--prefix', type=Path, required=True, help='native Ports prefix with cmake, ninja and libuv')
    parser.add_argument('--cross', nargs=3, type=Path, required=True, metavar=('MAKE', 'MAKECONF', 'PKGSRC'),
                        help='cross bmake wrapper, cross MAKECONF and the exported pkgsrc tree')
    parser.add_argument('work', type=Path, help='new work directory')
    args = parser.parse_args()
    args.work.mkdir()
    try:
        problem = native(args.distfile, args.cross[2], args.prefix, args.work) or cross(*args.cross)
    except subprocess.CalledProcessError as error:
        problem = ' '.join(map(str, error.cmd)) + ' fails: ' + (error.stderr or error.stdout).strip()[-500:]
    if problem:
        print('FAIL: ' + problem)
        return 1
    shutil.rmtree(args.work)
    print('PASS: the uvwasi consumer links to the versioned library')
    return 0


if __name__ == '__main__':
    sys.exit(main())
