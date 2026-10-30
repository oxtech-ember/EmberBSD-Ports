#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check that pkgsrc's tar extracts every LLD EXTRACT_ELEMENTS pattern.

The pkgsrc tar consumes an archive member with the first matching pattern,
so a pattern nested below another element is reported as not matched and
fails the extract phase.  Build a small archive with the members the test
build needs and extract it with the selected tar and the recipe's elements.
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tarfile


def run(argv, **kwargs):
    return subprocess.run(list(map(str, argv)), check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True, type=Path)
    parser.add_argument('--pkgsrc', required=True, type=Path,
                        help='pinned combined pkgsrc export used by the native profile')
    parser.add_argument('--makeconf', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--environment', action='append', default=[],
                        help='NAME=VALUE passed to bmake (repeatable)')
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

    env = dict(os.environ)
    env.update(item.split('=', 1) for item in args.environment)
    wrkdir = args.work / 'work'
    common = [args.bmake, '-C', fixture / 'devel/lld',
              'MAKECONF=' + str(args.makeconf.resolve(strict=True)),
              'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'PKG_OPTIONS.lld=tests',
              'WRKDIR=' + str(wrkdir)]

    def value(name):
        return run([*common, '-V', '${' + name + '}'], env=env)

    distname = value('DISTNAME')
    elements = value('EXTRACT_ELEMENTS').split()
    if not elements:
        raise SystemExit('LLD recipe selects no EXTRACT_ELEMENTS')
    run([*common, 'tools'], env=env)
    tar = wrkdir / '.tools/bin/tar'
    tar.resolve(strict=True)

    # One file at or below every element, plus the GoogleTest main the unit tests use.
    test_main = distname + '/third-party/unittest/UnitTestMain/TestMain.cpp'
    members = [element if Path(element).suffix else element + '/fixture.txt'
               for element in elements]
    if test_main not in members:
        members.append(test_main)
    source = args.work / 'source'
    for member in members:
        path = source / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(member + '\n')
    archive = args.work / 'fixture.tar'
    with tarfile.open(archive, 'w', format=tarfile.USTAR_FORMAT) as stream:
        stream.add(source / distname, arcname=distname)

    output = args.work / 'extract'
    output.mkdir()
    result = subprocess.run([str(tar), '-xf', str(archive), *elements], cwd=output,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    if result.returncode != 0:
        raise SystemExit('pkgsrc tar rejected the LLD EXTRACT_ELEMENTS:\n' + result.stdout)
    missing = [member for member in members if not (output / member).is_file()]
    if missing:
        raise SystemExit('LLD extract left out: ' + ', '.join(missing))
    print(f'PASS: pkgsrc tar extracts all {len(elements)} LLD elements, including TestMain.cpp')


if __name__ == '__main__':
    main()
