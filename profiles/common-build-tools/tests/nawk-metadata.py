#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc awk replacement controls.
"""Check the common awk provider floor without reading or changing a package database."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('tools-mk', 'bmake', 'pkg-admin', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args()
    args.work.mkdir()
    source = args.tools_mk.read_text()
    start = source.index('.if !defined(TOOLS_IGNORE.awk)')
    end = source.index('.if !defined(TOOLS_IGNORE.bash)', start)
    selected = args.work / 'awk-replacement.mk'
    selected.write_text(source[start:end])
    env = dict(os.environ, MAKEFLAGS='', MAKECONF='/dev/null', LC_ALL='C')
    results = {}
    failures = []
    for label, package, use, custom in (
        ('default', 'test/consumer', 'yes', None),
        ('custom', 'test/consumer', 'yes', 'nawk>=99999999:../../lang/nawk'),
        ('self', 'lang/nawk', 'yes', None),
        ('unselected', 'test/consumer', 'no', None)):
        fixture = args.work / (label + '.mk')
        fixture.write_text('_USE_TOOLS=awk\n_TOOLS_USE_PKGSRC.awk=' + use + '\n'
            + 'TOOLBASE=/selected/native\nPKGPATH=' + package + '\n'
            + (('TOOLS_DEPENDS.awk=' + custom + '\n') if custom else '')
            + '.include "' + str(selected) + '"\n')
        process = subprocess.run([str(args.bmake), '-r', '-f', str(fixture),
            '-V', '${TOOLS_DEPENDS.awk}', '-V', '${TOOLS_PATH.awk}', '-V', '${MAKEFLAGS}'],
            env=env, capture_output=True, text=True, check=True)
        (args.work / (label + '.out')).write_text(process.stdout)
        rows = process.stdout.splitlines()
        dependency, route, flags = rows
        accepted = {}
        for version in ('20250726', '20260426', '99999999'):
            pattern = dependency.partition(':')[0]
            match = subprocess.run([str(args.pkg_admin), 'pmatch', pattern, 'nawk-' + version],
                env=env, capture_output=True) if pattern else None
            if match is not None and match.returncode not in (0, 1):
                raise ValueError('pkgsrc matcher failed')
            accepted[version] = match is not None and match.returncode == 0
        if label == 'default':
            valid = accepted == {'20250726': False, '20260426': True, '99999999': True} and route == '/selected/native/bin/nawk'
        elif label == 'custom':
            valid = accepted == {'20250726': False, '20260426': False, '99999999': True} and dependency == custom
        elif label == 'self':
            valid = not dependency and not route and 'TOOLS_IGNORE.awk=' in flags
        else:
            valid = not dependency and not route
        results[label] = dict(dependency=dependency, route=route, accepted=accepted, valid=valid)
        if not valid:
            failures.append(label)
    (args.work / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    if failures:
        raise ValueError('awk replacement metadata failed: ' + ', '.join(failures))
    print('PASS: actual common replacement floor, old-provider refusal, stronger caller, self-cycle and unselected controls')
    print('No package database access, compilation or prefix mutation')


if __name__ == '__main__':
    main()
