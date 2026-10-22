#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check native CMake routing in the real ebook-tools cross metadata."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'bmake', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    source = args.pkgsrc.resolve(strict=True)
    work = args.work.absolute()
    work.mkdir()
    tree = work / 'pkgsrc'
    tree.mkdir()
    # Only the changed recipe is writable. The baseline stays unchanged.
    for path in source.iterdir():
        if path.name != 'textproc':
            (tree / path.name).symlink_to(path, target_is_directory=path.is_dir())
    (tree / 'textproc').mkdir()
    for path in (source / 'textproc').iterdir():
        if path.name != 'ebook-tools':
            (tree / 'textproc' / path.name).symlink_to(path, target_is_directory=path.is_dir())
    recipe = tree / 'textproc/ebook-tools'
    shutil.copytree(source / 'textproc/ebook-tools', recipe, symlinks=True)
    keys = ('PKGNAME', 'BUILD_DEPENDS', 'DEPENDS', 'TOOL_DEPENDS',
            'USE_CROSS_COMPILE', 'CC', 'CMAKE')

    def query(label):
        argv = [str(args.bmake.resolve()), '-C', str(recipe),
                'MAKECONF=' + str(args.makeconf.resolve()), 'USE_CROSS_COMPILE=yes']
        for key in keys:
            argv.extend(('-V', '${' + key + '}'))
        result = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        (work / (label + '.stderr')).write_text(result.stderr)
        if result.returncode:
            raise SystemExit('Metadata query failed: ' + label)
        values = result.stdout.splitlines()
        if len(values) != len(keys):
            raise SystemExit('Unexpected metadata shape.')
        row = dict(zip(keys, values))
        (work / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
        return row

    before = query('before')
    root = Path(__file__).resolve().parents[3]
    patch = root / 'profiles/common-build-tools/patches/pkgsrc-ebook-tools-host-cmake.patch'
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=tree, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=tree, check=True)
    after = query('after')
    assert ':../../devel/cmake' in before['BUILD_DEPENDS']
    assert ':../../devel/cmake' not in after['BUILD_DEPENDS'] + after['DEPENDS']
    for key in ('TOOL_DEPENDS', 'USE_CROSS_COMPILE', 'CC', 'CMAKE', 'DEPENDS'):
        assert before[key] == after[key], key
    assert after['USE_CROSS_COMPILE'] == 'yes'
    assert 'aarch64--netbsd-gcc' in after['CC']
    assert 'libzip' in after['DEPENDS'] and 'libxml2' in after['DEPENDS']
    assert after['PKGNAME'] == 'ebook-tools-0.2.2nb30'
    print('PASS: native CMake selection and target library dependencies are preserved.')


if __name__ == '__main__':
    main()
