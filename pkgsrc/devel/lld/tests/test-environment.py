#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check pkgsrc's actual LLD test tool/dependency/locale setup."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess


def run(argv, **kwargs):
    return subprocess.run(list(map(str, argv)), check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True, type=Path)
    parser.add_argument('--pkgsrc', required=True, type=Path,
                        help='pinned combined pkgsrc export used by the native profile')
    parser.add_argument('--makeconf', required=True, type=Path)
    parser.add_argument('--host-prefix', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()

    pkgsrc = args.pkgsrc.resolve(strict=True)
    recipe = Path(__file__).resolve().parent.parent
    args.work = args.work.absolute()
    args.work.mkdir(parents=True, exist_ok=False)
    fixture = args.work / 'pkgsrc'
    fixture.mkdir()
    for entry in pkgsrc.iterdir():
        if entry.name == 'devel':
            continue
        (fixture / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    (fixture / 'devel').mkdir()
    for entry in (pkgsrc / 'devel').iterdir():
        if entry.name == 'lld':
            continue
        (fixture / 'devel' / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    shutil.copytree(recipe, fixture / 'devel/lld')

    wrkdir = args.work / 'work'
    package = fixture / 'devel/lld'
    common = [args.bmake, '-C', package,
              'MAKECONF=' + str(args.makeconf.resolve(strict=True)),
              'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'PKG_OPTIONS.lld=tests',
              'WRKDIR=' + str(wrkdir)]

    def value(name):
        return run([*common, '-V', name])

    use_tools = value('USE_TOOLS').split()
    if 'od:test' not in use_tools:
        raise SystemExit('LLD tests do not select od:test through pkgsrc tools')
    selected = Path(value('TOOLS_PATH.od')).resolve(strict=True)
    expected = (args.host_prefix.resolve(strict=True) / 'gnu/bin/od').resolve(strict=True)
    if selected != expected:
        raise SystemExit(f'od selected outside the native prefix: {selected}')
    test_env = value('TEST_ENV').split()
    if 'LC_ALL=C' not in test_env or not any(item.startswith('LD_LIBRARY_PATH=') for item in test_env):
        raise SystemExit('LLD tests must retain their build library path and select the C locale')
    test_depends = value('TEST_DEPENDS')
    if 'coreutils' not in test_depends or '../../sysutils/coreutils' not in test_depends:
        raise SystemExit('pkgsrc did not place coreutils in the test dependency phase')

    run([*common, 'tools'])
    od_wrapper = wrkdir / '.tools/bin/od'
    if od_wrapper.resolve(strict=True) != expected:
        raise SystemExit('pkgsrc od wrapper does not execute the selected coreutils binary')
    sample = args.work / 'sample.bin'
    sample.write_bytes(b'A')
    output = run([od_wrapper, '-An', '-tx1', sample])
    if output.lower() != '41':
        raise SystemExit('selected od wrapper produced unexpected output: ' + output)

    dated = args.work / 'dated'
    dated.touch()
    os.utime(dated, (1706788800, 1706788800))
    locale_env = dict(os.environ, LC_ALL='C')
    listing = subprocess.run(['/bin/ls', '-l', dated], check=True, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=locale_env).stdout
    if 'Feb' not in listing:
        raise SystemExit('C locale did not make the LLD ls fixture deterministic')
    print('PASS: pkgsrc test dependency, selected od wrapper, and C locale')


if __name__ == '__main__':
    main()
