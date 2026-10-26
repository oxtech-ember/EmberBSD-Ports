#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Evaluate the common Binutils recipe with a real exported pkgsrc framework.

Only metadata queries run. The framework is read-only; the recipe and an empty
package database live in the test's temporary directory.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

PORTS = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--make-arg', action='append', required=True,
                        help='Complete selected make argv, repeated once per argument')
    parser.add_argument('--environment', type=Path, required=True,
                        help='Renderer JSON containing the explicit metadata environment')
    args = parser.parse_args()
    exported = args.pkgsrc.resolve(strict=True)
    env = json.loads(args.environment.read_text())['environment']
    with tempfile.TemporaryDirectory(prefix='binutils-zlib-') as temporary:
        work = Path(temporary).resolve()
        tree = work / 'pkgsrc'
        tree.mkdir()
        for entry in exported.iterdir():
            if entry.name != 'devel':
                (tree / entry.name).symlink_to(entry)
        (tree / 'devel').mkdir()
        for entry in (exported / 'devel').iterdir():
            if entry.name != 'binutils':
                (tree / 'devel' / entry.name).symlink_to(entry)
        recipe = tree / 'devel/binutils'
        shutil.copytree(PORTS / 'pkgsrc/devel/binutils', recipe)
        package_db = work / 'pkgdb'
        package_db.mkdir()
        variables = ('PKGNAME', 'CONFIGURE_ARGS', 'BUILDLINK_TREE', 'DEPENDS', 'USE_BUILTIN.zlib')
        command = [*args.make_arg, '-C', str(recipe), 'PKG_DBDIR=' + str(package_db),
                   'WRKOBJDIR=' + str(work / 'objects')]
        for name in variables:
            command += ['-V', '${' + name + '}']
        result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
        if result.returncode or result.stderr:
            raise RuntimeError(result.stdout + result.stderr)
        values = dict(zip(variables, result.stdout.splitlines(), strict=True))
        assert values['PKGNAME'] == 'binutils-2.47nb3', values
        assert '--with-system-zlib' in values['CONFIGURE_ARGS'].split(), values
        assert 'zlib' in values['BUILDLINK_TREE'].split(), values
        assert any(word.startswith('zlib>=') and word.endswith(':../../devel/zlib')
                   for word in values['DEPENDS'].split()), values
        assert values['USE_BUILTIN.zlib'] == 'no', values
        result = subprocess.run([*args.make_arg, '-r', '-f', str(recipe / 'buildlink3.mk'),
                                 '-V', '${BUILDLINK_ABI_DEPENDS.binutils}'],
                                cwd=work, env=env, text=True, capture_output=True, timeout=30)
        assert result.returncode == 0 and not result.stderr, result.stdout + result.stderr
        assert result.stdout.strip() == 'binutils>=2.47nb3', result.stdout
        print('PASS: real Binutils metadata selects common zlib, system-zlib configure and nb3 ABI floor')


if __name__ == '__main__':
    main()
