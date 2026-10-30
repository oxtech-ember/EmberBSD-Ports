#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that each package stamp-source.py hashes its staged tree once.

The stamp helpers wrote the SDK prepared-tree receipt, which measures the
whole tree, and then validated it at once, which measured the whole tree
again. For lang/v8 that is a second full read of a large source tree in
every build. The test runs every helper against a copy of the selected SDK
whose tree digest logs each call, requires exactly one call, and then
checks the receipt with the SDK's own validation.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PACKAGES = ('lang/v8', 'devel/gyp', 'devel/inspector-protocol', 'security/boringssl')
COUNTER = '''

_counted_prepared_tree_digest = _prepared_tree_digest


def _prepared_tree_digest(root):
    with open(os.environ['STAMP_DIGEST_LOG'], 'a') as handle:
        handle.write(str(root) + '\\n')
    return _counted_prepared_tree_digest(root)
'''
IDENTITY = '''def effective_package_identity(root, package, upstream):
    return {'package': package, 'upstream': upstream}
'''


def fail(message):
    raise SystemExit('FAIL: ' + message)


def populate(path):
    (path / 'src').mkdir(parents=True)
    (path / 'src/a.cc').write_text('int a;\n')
    (path / 'README').write_text('payload\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    ports = Path(__file__).resolve().parents[2]
    sdk = args.sdk_source.resolve(strict=True)
    work = args.work.resolve()
    if work.exists():
        parser.error('Work directory already exists')
    work.mkdir(parents=True)
    counted = work / 'sdk'
    shutil.copytree(sdk / 'src', counted / 'src',
                    ignore=shutil.ignore_patterns('__pycache__'))
    with open(counted / 'src/emberbsd_sdk/sourceprep.py', 'a') as handle:
        handle.write(COUNTER)
    tree = work / 'pkgsrc'
    shutil.copytree(ports / 'pkgsrc/lang/llvm/files', tree / 'lang/llvm/files',
                    ignore=shutil.ignore_patterns('__pycache__'))
    (tree / 'EMBERBSD-PKGSRC-REVISION').write_text('0' * 40 + '\n')
    (tree / 'EMBERBSD-SOURCE-IDENTITY').mkdir()
    (tree / 'EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py').write_text(IDENTITY)
    log = work / 'digest.log'
    env = dict(os.environ, STAMP_DIGEST_LOG=str(log))
    sys.path.insert(0, str(sdk / 'src'))
    from emberbsd_sdk import sourceprep

    def run(package, extra, source, identity):
        script = tree / package / 'files/stamp-source.py'
        script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ports / 'pkgsrc' / package / 'files/stamp-source.py', script)
        log.write_text('')
        result = subprocess.run([sys.executable, '-B', '-I', '-S', str(script),
                                 '--sdk-source', str(counted), '--source', str(source)] + extra,
                                env=env, stdin=subprocess.DEVNULL, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            fail(f'{package} stamp-source.py failed: {result.stderr.strip()}')
        calls = log.read_text().splitlines()
        if len(calls) != 1:
            fail(f'{package} hashed its tree {len(calls)} times')
        sourceprep.validate_prepared_tree(str(source), package=package, identity=identity)

    for package in PACKAGES:
        source = work / 'staged' / package
        populate(source)
        run(package, ['--pkgsrc-root', str(tree)], source,
            {'effective': {'package': package, 'upstream': '0' * 40}})
    runtime = work / 'runtime'
    populate(runtime / 'libc')
    record = {'format': 'emberbsd-llvm-source', 'version': 2, 'llvm_version': '22.1.0',
              'components': ['libc'], 'source': {'archive': 'llvm.tar.xz'},
              'recipe': {'files': {'Makefile': '0' * 64}}}
    (runtime / 'llvm-source.json').write_text(json.dumps(record))
    source = work / 'staged/lang/llvm-libc-source'
    populate(source)
    run('lang/llvm-libc-source', ['--runtime-source', str(runtime)], source,
        {'llvm_version': '22.1.0', 'source': record['source'],
         'runtime_recipe_files': record['recipe']['files']})
    print('PASS: every stamp-source.py hashes its tree once and writes a valid receipt')


if __name__ == '__main__':
    main()
