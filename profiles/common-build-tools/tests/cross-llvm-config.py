#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that cross clang and lld make their build-host llvm-config.

The bulk order phase evaluates clang and lld before lang/llvm is built.
EMBERBSD_CROSS_LLVM_CONFIG must not be a PKG_FAIL_REASON there. The
pre-configure step lang/llvm/cross-llvm-config.mk must make it from the
lang/llvm build tree, use an existing one as it is, and keep failed work.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
RECIPES = ('lang/clang', 'devel/lld')
VERSION = '23.1.4'


def make(cross, pkgpath, *arguments):
    tool, makeconf, pkgsrc = cross
    return subprocess.run([str(tool), *arguments], cwd=pkgsrc / pkgpath,
                          env=dict(os.environ, MAKECONF=str(makeconf)), capture_output=True, text=True)


def recipes(cross):
    for pkgpath in RECIPES:
        result = make(cross, pkgpath, '-V', '${PKG_FAIL_REASON}', '-V', '${LLVM_CONFIG_PATH}')
        values = result.stdout.splitlines()
        if result.returncode != 0 or len(values) != 2:
            return 'cannot evaluate ' + pkgpath + ': ' + result.stderr.strip()[:300]
        failure, config = values
        if 'EMBERBSD_CROSS_LLVM_CONFIG' in failure:
            return pkgpath + ' fails before lang/llvm is built: ' + failure.strip()[:300]
        if not config.endswith('/llvm-config-' + VERSION + '/sealed/bin/llvm-config') or '/.emberbsd-cross/' not in config:
            return pkgpath + ' does not select the made llvm-config: ' + config
        result = make(cross, pkgpath, '-n', 'emberbsd-cross-llvm-config')
        if result.returncode != 0 or 'lang/llvm/files/cross-llvm-config.py' not in result.stdout \
                or 'llvm-project-' + VERSION + '.src.tar.xz' not in result.stdout:
            return pkgpath + ' has no pre-configure llvm-config step: ' + (result.stdout + result.stderr).strip()[:300]
    return None


def helper(script):
    """Run the helper only on paths where it must stop before any build."""
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        existing = root / 'existing-llvm-config'
        existing.write_text('#!/bin/sh\necho ' + VERSION + '\n')
        existing.chmod(0o755)
        work = root / ('state/llvm-config-' + VERSION)
        default = str(work / 'sealed/bin/llvm-config')
        common = [str(root / 'state/llvm-native'), str(root / 'pkgsrc'), str(root / 'sysroot'),
                  str(root / 'archive.tar.xz'), '/nonexistent-make']
        environment = {k: v for k, v in os.environ.items() if k != 'EMBERBSD_HOST_PREFIX'}

        def run(config):
            return subprocess.run([sys.executable, '-B', str(script), config, str(work), *common],
                                  capture_output=True, text=True, env=environment)
        if run(str(existing)).returncode != 0:
            return 'an existing llvm-config is not used'
        result = run(str(root / 'other-llvm-config'))
        if result.returncode == 0 or 'does not report LLVM' not in result.stderr:
            return 'a missing EMBERBSD_CROSS_LLVM_CONFIG is accepted'
        work.mkdir(parents=True)
        result = run(default)
        if result.returncode == 0 or not work.is_dir() or 'examine it' not in result.stderr:
            return 'failed work is accepted or removed'
        work.rmdir()
        result = run(default)
        if result.returncode == 0 or 'EMBERBSD_HOST_PREFIX' not in result.stderr or work.exists():
            return 'the helper starts without the native Ports prefix'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cross', nargs=3, type=Path, required=True, metavar=('MAKE', 'MAKECONF', 'PKGSRC'),
                        help='cross bmake wrapper, cross MAKECONF and the exported pkgsrc tree')
    args = parser.parse_args()
    script = args.cross[2] / 'lang/llvm/files/cross-llvm-config.py'
    problem = recipes(args.cross) or (None if script.is_file() else 'no ' + str(script)) or helper(script)
    if problem:
        print('FAIL: ' + problem)
        return 1
    print('PASS: cross clang and lld make the build-host llvm-config before configure')
    return 0


if __name__ == '__main__':
    sys.exit(main())
