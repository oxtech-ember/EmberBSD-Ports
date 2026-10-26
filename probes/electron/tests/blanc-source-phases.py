#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), actual pkgsrc phase regression.
"""Exercise Blanc source/build phase boundaries with a real pkgsrc framework.

The optional distdir must already contain all recipe inputs. The test then runs
normal pkgsrc fetch/checksum without selected application build tools. No Node,
ASAR build, target code or dependency installation is performed.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
RECIPE = ROOT / 'probes/electron/blanc'
SELECTED = ('EMBERBSD_SDK_SOURCE', 'EMBERBSD_CROSS_BUILD_PYTHON', 'EMBERBSD_HOST_NODE')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def framework_view(source, destination, recipe):
    destination.mkdir()
    for item in source.iterdir():
        if item.name not in ('www', '.git'):
            (destination / item.name).symlink_to(item, target_is_directory=item.is_dir())
    (destination / 'www').mkdir()
    for item in (source / 'www').iterdir():
        if item.name != 'blanc':
            (destination / 'www' / item.name).symlink_to(item, target_is_directory=item.is_dir())
    shutil.copytree(RECIPE, destination / 'www/blanc')
    shutil.copyfile(recipe, destination / 'www/blanc/Makefile')
    return destination / 'www/blanc'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'bmake', 'make-mk', 'shell', 'makeconf', 'env-json',
                 'sdk-source', 'python', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--distdir', type=Path)
    parser.add_argument('--baseline-recipe', type=Path)
    parser.add_argument('--make-arg', action='append', default=[])
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path):
            require(value.is_absolute(), f'{name} must be absolute')
    require((args.pkgsrc / 'mk/bsd.pkg.mk').is_file(), 'Use an actual pkgsrc export')
    require((args.sdk_source / 'src/emberbsd_sdk/__init__.py').is_file(), 'SDK source is missing')
    require(not os.path.lexists(args.work), 'Use a new test work directory')
    args.work.mkdir(parents=True)
    (args.work / 'tmp').mkdir()
    env = json.loads(args.env_json.read_text())
    env = env.get('environment', env)
    require(isinstance(env, dict) and all(isinstance(k, str) and isinstance(v, str)
            for k, v in env.items()), 'Environment must contain string pairs')
    for key in SELECTED:
        env.pop(key, None)
    env['TMPDIR'] = str(args.work / 'tmp')
    package = framework_view(args.pkgsrc, args.work / 'candidate', RECIPE / 'Makefile')
    command = [str(args.bmake), '-m', str(args.make_mk), 'SHELL=' + str(args.shell),
               'MAKECONF=' + str(args.makeconf), *args.make_arg,
               'BUILD_DIR=' + str(args.work / 'objects'),
               'WRKDIR=' + str(args.work / 'objects/work'),
               'PACKAGES=' + str(args.work / 'packages')]
    empty = [key + '=' for key in SELECTED]
    accepted = ['ACCEPTABLE_LICENSES+=blueoak-1.0.0']
    source_tools = ['EMBERBSD_SDK_SOURCE=' + str(args.sdk_source),
                    'EMBERBSD_CROSS_BUILD_PYTHON=' + str(args.python)]
    cases = []

    def run(label, targets, extra=(), *, success=True, contains=None, cwd=package):
        result = subprocess.run(command + empty + list(extra) + list(targets),
                                cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
        (args.work / (label + '.stdout')).write_text(result.stdout)
        (args.work / (label + '.stderr')).write_text(result.stderr)
        require((result.returncode == 0) == success,
                f'{label}: unexpected exit {result.returncode}: {result.stdout}{result.stderr}')
        if contains:
            require(contains in result.stdout + result.stderr, f'{label}: missing {contains!r}')
        cases.append(label)
        return result.stdout

    reason = run('license-still-required', ['-V', '${PKG_FAIL_REASON}'],
                 extra=['ACCEPTABLE_LICENSES='], contains='unacceptable license condition')
    require('Blanc requires' not in reason, 'Source metadata must not require build tools')
    require('blueoak-1.0.0' in reason, 'License restriction was lost')
    require(run('accepted-source-metadata', ['-V', '${PKG_FAIL_REASON}'], accepted).strip() == '',
            'Unexpected fetch failure with accepted licenses')
    files = run('source-distfiles', ['show-distfiles'], accepted).splitlines()
    manifest = json.loads((RECIPE / 'files/npm-mirror-manifest.json').read_text())
    expected = {'e12-electron/v1.25.0.tar.gz'} | {
        'e12-electron/' + row['distfile'] for row in manifest['packages']}
    require(set(files) == expected and len(files) == len(expected) == 41,
            'Actual pkgsrc source inventory is incomplete')
    if args.baseline_recipe:
        baseline = framework_view(args.pkgsrc, args.work / 'baseline', args.baseline_recipe)
        before = run('causal-baseline-metadata', ['-V', '${PKG_FAIL_REASON}'], accepted,
                     cwd=baseline, contains='EMBERBSD_HOST_NODE')
        require('emberbsd_sdk_source' in before.lower() and 'EMBERBSD_CROSS_BUILD_PYTHON' in before,
                'Baseline must reproduce the global source acquisition failure')
        require(not run('causal-baseline-distfiles', ['show-distfiles'], accepted,
                        cwd=baseline).strip(), 'Baseline unexpectedly exposes source inputs')
    run('extract-missing-sdk', ['pre-extract'], success=False, contains='EMBERBSD_SDK_SOURCE')
    run('extract-missing-python', ['pre-extract'], source_tools[:1], success=False,
        contains='EMBERBSD_CROSS_BUILD_PYTHON')
    run('extract-relative-python', ['pre-extract'],
        [source_tools[0], 'EMBERBSD_CROSS_BUILD_PYTHON=python3'], success=False,
        contains='EMBERBSD_CROSS_BUILD_PYTHON')
    run('extract-without-node', ['pre-extract'], source_tools)
    for target in ('pre-build', 'pre-test', 'do-build', 'do-test'):
        run(target + '-missing-node', [target], source_tools, success=False,
            contains='EMBERBSD_HOST_NODE')
    run('build-relative-node', ['pre-build'], source_tools + ['EMBERBSD_HOST_NODE=node'],
        success=False, contains='EMBERBSD_HOST_NODE')
    run('build-missing-node-file', ['pre-build'],
        source_tools + ['EMBERBSD_HOST_NODE=' + str(args.work / 'missing-node')],
        success=False, contains='EMBERBSD_HOST_NODE')
    require(not (args.work / 'objects/work/app-stage').exists(), 'A build unexpectedly started')
    if args.distdir:
        require(all((args.distdir / path).is_file() for path in expected),
                'All inputs must already be cached: this regression does not download')
        run('fetch-retains-license-check', ['fetch'],
            ['ACCEPTABLE_LICENSES=', 'DISTDIR=' + str(args.distdir)], success=False,
            contains='unacceptable license condition')
        run('normal-fetch-checksum-without-build-tools', ['fetch', 'checksum'],
            accepted + ['DISTDIR=' + str(args.distdir)])
        corrupted = args.work / 'corrupted-distfiles'
        (corrupted / 'e12-electron').mkdir(parents=True)
        for relative in expected:
            target = corrupted / relative
            if relative == 'e12-electron/ms-2.1.3.tgz':
                target.write_bytes(b'corrupted input')
            else:
                target.symlink_to(args.distdir / relative)
        run('checksum-rejects-corrupted-input', ['checksum'],
            accepted + ['DISTDIR=' + str(corrupted)], success=False, contains='Checksum')
    print(json.dumps(dict(status='PASS', cases=cases,
        scope='Real pkgsrc metadata, phase failures, and optional cached fetch/checksum; no build')))


if __name__ == '__main__':
    main()
