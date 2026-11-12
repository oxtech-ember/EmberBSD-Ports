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
MANIFEST = (ROOT / 'pkgsrc/export.conf').read_text().splitlines()
def is_node_line(line):
    fields = line.split('\t')
    if fields[0] == 'file':
        return len(fields) == 3 and fields[2].startswith('lang/nodejs/')
    if fields[0] == 'recipe-patch':
        return len(fields) == 4 and fields[2] == 'lang/nodejs'
    if fields[0] != 'patch' or len(fields) != 2:
        return False
    path = ROOT / fields[1]
    headers = [x[6:] for x in path.read_text().splitlines() if x.startswith('--- a/')]
    return bool(headers) and all(x.startswith('lang/nodejs/') for x in headers)

NODE_LINES = [line for line in MANIFEST if is_node_line(line)]
NODE_RECIPE_PATCHES = [(Path(line.split('\t')[1]), line.split('\t')[3])
                       for line in NODE_LINES if line.startswith('recipe-patch\t')]
NODE_PATCH_FILES = [Path(line.split('\t')[1]) for line in NODE_LINES]
assert PATCH in NODE_PATCH_FILES
EXPORT_LINE = '\n'.join(NODE_LINES) + '\n'



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
    for patch_file in NODE_PATCH_FILES:
        destination = ports / patch_file
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / patch_file).read_bytes())
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
    assert any(name.endswith('node-emudhra-rsa-blocklist') for _, name in NODE_RECIPE_PATCHES)
    for source, name in NODE_RECIPE_PATCHES:
        assert (recipe / 'patches' / name).read_bytes() == (ROOT / source).read_bytes()
        assert (f'SHA1 ({name}) = {EXPORTER.patch_sha1(ROOT / source)}\n') in (recipe / 'distinfo').read_text()
    assert not list(destination.rglob('*.~[0-9]*~'))
    print('PASS: common exporter applied Node.js 26 recipe overlay with selected patch tool')


if __name__ == '__main__':
    main()
