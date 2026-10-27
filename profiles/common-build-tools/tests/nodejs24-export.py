#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the common pkgsrc exporter with the Node.js 24 Python patch."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'ports_exporter', ROOT / 'scripts/prepare-pkgsrc.py')
EXPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORTER)
PATCH = Path('profiles/common-build-tools/patches/pkgsrc-nodejs24-python315.patch')
EXPORT_LINE = 'patch\t' + PATCH.as_posix() + '\n'


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
    package = upstream / 'lang/nodejs24'
    (ports / 'pkgsrc').mkdir(parents=True)
    package.mkdir(parents=True)
    (ports / 'profiles/common-build-tools/patches').mkdir(parents=True)
    (ports / 'profiles/common-build-tools/patches' / PATCH.name).write_bytes(
        (ROOT / PATCH).read_bytes())
    (ports / 'pkgsrc/export.conf').write_text(EXPORT_LINE)
    (package / 'Makefile').write_text(
        '# $NetBSD: Makefile,v 1.17 2026/09/09 07:30:58 adam Exp $\n\n'
        'DISTNAME=\tnode-v24.22.1\nPKGREVISION=\t2\nEXTRACT_SUFX=\t.tar.xz\n\n'
        'USE_LANGUAGES=\tc c++\n')
    (package / 'distinfo').write_text(
        'SHA1 (patch-tools_gyp_pylib_gyp_xcode__emulation.py) = 4ee24115f5e97ffbd23aaa6dc62f408d381d4e22\n'
        'SHA1 (patch-tools_install.py) = ac296123fa498c7edee3a5735f2e24c862037813\n'
        'SHA1 (patch-tools_v8_gypfiles_v8.gyp) = 112aa21cb2c2c4609cba96f41ae306d6e60ae797\n')

    subprocess.run([str(args.git), '-C', str(upstream), 'init', '-q'], check=True)
    subprocess.run([str(args.git), '-C', str(upstream), 'add', 'lang/nodejs24'], check=True)
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
    recipe = destination / 'lang/nodejs24'
    assert (recipe / 'patches/patch-configure').is_file()
    assert (recipe / 'patches/patch-tools_gyp_pylib_gyp_input.py').is_file()
    assert 'PKGREVISION=\t3\n' in (recipe / 'Makefile').read_text()
    assert 'SHA1 (patch-configure) = fa89560fffeebf7c6b9bc07bb9327cc7d837388c' in (recipe / 'distinfo').read_text()
    assert not list(destination.rglob('*.~[0-9]*~'))
    print('PASS: common exporter applied Node.js Python 3.15 patch with selected patch tool')


if __name__ == '__main__':
    main()
