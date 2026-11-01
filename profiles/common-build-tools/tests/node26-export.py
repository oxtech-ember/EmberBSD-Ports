#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the common pkgsrc exporter with the Node.js 26 recipe overlay."""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'ports_exporter', ROOT / 'scripts/prepare-pkgsrc.py')
EXPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORTER)
PATCH = Path('profiles/common-build-tools/patches/pkgsrc-nodejs-current.patch')
CRYPTO_PATCH = Path('profiles/common-build-tools/patches/node-crypto-provider-types.patch')
EXPORT_LINE = ('patch\t' + PATCH.as_posix() + '\n' +
               'recipe-patch\t' + CRYPTO_PATCH.as_posix() +
               '\tlang/nodejs\tpatch-zzzzzzzzzz-node-crypto-provider-types\n')


def run(command, *, cwd=None, input=None):
    env = dict(os.environ, LC_ALL='C', GIT_OPTIONAL_LOCKS='0',
               GIT_NO_LAZY_FETCH='1', PATCH_VERSION_CONTROL='none')
    result = subprocess.run(command, cwd=cwd, input=input, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env, check=False)
    if result.returncode:
        raise RuntimeError('command failed: ' + repr(command) + '\n' +
                           result.stdout.decode(errors='replace') +
                           result.stderr.decode(errors='replace'))
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--expected-recipe', type=Path, required=True)
    parser.add_argument('--git', type=Path, required=True)
    parser.add_argument('--patch', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    for path in (args.git, args.patch):
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            parser.error('select absolute executable git and patch paths')
    version = subprocess.run([str(args.patch), '--version'], check=True, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    if 'GNU patch' not in version:
        parser.error('this regression requires GNU patch')
    if not args.work.is_absolute() or args.work.exists():
        parser.error('use a new absolute work directory')

    ports = args.work / 'ports'
    upstream = ports / 'upstream/pkgsrc'
    package = upstream / 'lang/nodejs'
    (ports / 'pkgsrc').mkdir(parents=True)
    import shutil
    shutil.copytree(args.pkgsrc / 'lang/nodejs', package)
    (ports / 'profiles/common-build-tools/patches').mkdir(parents=True)
    for patch_file in (PATCH, CRYPTO_PATCH):
        (ports / 'profiles/common-build-tools/patches' / patch_file.name).write_bytes(
            (ROOT / patch_file).read_bytes())
    (ports / 'pkgsrc/export.conf').write_text(EXPORT_LINE)
    subprocess.run([str(args.git), '-C', str(upstream), 'init', '-q'], check=True)
    subprocess.run([str(args.git), '-C', str(upstream), 'add', '-f', 'lang/nodejs'], check=True)
    subprocess.run([str(args.git), '-C', str(upstream), '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'],
                   check=True)
    revision = subprocess.run([str(args.git), '-C', str(upstream), 'rev-parse', 'HEAD'],
                              check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    subprocess.run([str(args.git), '-C', str(ports), 'init', '-q'], check=True)
    subprocess.run([str(args.git), '-C', str(ports), 'add', 'pkgsrc/export.conf'], check=True)
    subprocess.run([str(args.git), '-C', str(ports), 'update-index', '--add', '--cacheinfo',
                    '160000,' + revision + ',upstream/pkgsrc'], check=True)

    selected = type('SelectedTools', (), {
        'command': lambda self, role: (str(args.git if role == 'git' else args.patch),)
    })()
    destination = args.work / 'export'
    scratch = args.work / 'scratch'
    exported_revision = EXPORTER.export_pkgsrc(
        ports, destination, selection=selected, runner=run, scratch=scratch)
    assert exported_revision == revision
    recipe = destination / 'lang/nodejs'
    actual = {p.relative_to(recipe): p.read_bytes() for p in recipe.rglob('*') if p.is_file()}
    expected = {p.relative_to(args.expected_recipe): p.read_bytes()
                for p in args.expected_recipe.rglob('*') if p.is_file()}
    assert actual == expected, (actual.keys() ^ expected.keys())
    makefile = (recipe / 'Makefile').read_text()
    assert re.search(r'^PKGREVISION=\s+1$', makefile, re.M)
    crypto_patch_name = 'patch-zzzzzzzzzz-node-crypto-provider-types'
    crypto_patch_data = (recipe / 'patches' / crypto_patch_name).read_bytes()
    assert crypto_patch_data == (ROOT / CRYPTO_PATCH).read_bytes()
    assert (f'SHA1 ({crypto_patch_name}) = '
            f'{EXPORTER.patch_sha1(ROOT / CRYPTO_PATCH)}\n') in (recipe / 'distinfo').read_text()
    assert not list(destination.rglob('*.~[0-9]*~'))
    print('PASS: common exporter applied Node.js 26 recipe overlay with selected patch tool')


if __name__ == '__main__':
    main()
