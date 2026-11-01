#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that cross clang and lld make their build-host llvm-config.

The pre-configure step consumes the installed target devel metadata and the
selected native LLVM package. It must not require target/native CMake trees.
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
        if not config.endswith('/llvm-config-' + VERSION + '/helper/bin/llvm-config') or '/.emberbsd-cross/' not in config:
            return pkgpath + ' does not select the made llvm-config: ' + config
        result = make(cross, pkgpath, '-n', 'emberbsd-cross-llvm-config')
        if result.returncode != 0 or 'lang/llvm/files/cross-llvm-config.py' not in result.stdout \
                or 'build-installed-llvm-config.py' not in result.stdout:
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
        default = str(work / 'helper/bin/llvm-config')
        common = [str(root / 'pkgsrc'), str(root / 'sysroot')]
        Path(common[1]).mkdir()
        environment = {k: v for k, v in os.environ.items() if k != 'EMBERBSD_HOST_PREFIX'}

        producer = root / 'pkgsrc/lang/llvm/files/build-installed-llvm-config.py'
        producer.parent.mkdir(parents=True)
        producer.write_text('''import pathlib, sys
work = pathlib.Path(sys.argv[2])
work.mkdir(parents=True)
tool = work / 'helper/bin/llvm-config'
tool.parent.mkdir(parents=True)
tool.write_text('#!/bin/sh\\necho ' + '23.1.4' + '\\n')
tool.chmod(0o755)
''')

        def run(config, *, host=True):
            env = dict(environment)
            if host:
                env['EMBERBSD_HOST_PREFIX'] = str(root / 'host')
            return subprocess.run([sys.executable, '-B', str(script), config, str(work), *common],
                                  capture_output=True, text=True, env=env)
        result = run(str(existing))
        if result.returncode == 0 or 'target llvm-devel is not installed' not in result.stderr:
            return 'a same-version helper without installed target binding is accepted'
        result = run(str(root / 'other-llvm-config'))
        if result.returncode == 0:
            return 'a missing EMBERBSD_CROSS_LLVM_CONFIG is accepted'
        work.mkdir(parents=True)
        result = run(default)
        if result.returncode == 0 or not work.is_dir():
            return 'failed work is accepted or removed'
        work.rmdir()
        result = run(default, host=False)
        if result.returncode == 0 or 'EMBERBSD_HOST_PREFIX' not in result.stderr or work.exists():
            return 'the helper starts without the native Ports prefix'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cross', nargs=3, type=Path, required=True, metavar=('MAKE', 'MAKECONF', 'PKGSRC'),
                        help='cross bmake wrapper, cross MAKECONF and the exported pkgsrc tree')
    parser.add_argument('--helper-only', action='store_true',
                        help='exercise the installed-package wrapper fixture without querying a pkgsrc tree')
    args = parser.parse_args()
    script = args.cross[2] / 'lang/llvm/files/cross-llvm-config.py'
    problem = (None if args.helper_only else recipes(args.cross)) or \
        (None if script.is_file() else 'no ' + str(script)) or helper(script)
    if problem:
        print('FAIL: ' + problem)
        return 1
    print('PASS: cross clang and lld make the build-host llvm-config before configure')
    return 0


if __name__ == '__main__':
    sys.exit(main())
