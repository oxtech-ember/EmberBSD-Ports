#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that prepared source receipts hash their tree once.

The stamp helpers wrote the SDK prepared-tree receipt, which measures the
whole tree, and then validated it at once, which measured the whole tree
again. For lang/v8 that is a second full read of a large source tree in
every build. The test runs every helper against a copy of the selected SDK
whose tree digest logs each call, requires exactly one call, and then
checks the receipt with the SDK's own validation. The source owners under
scripts/ write their receipts through scripts/prepared_receipt.py; the test
runs that helper the same way, and scans every receipt writer for a full
validation right after the write.
"""

import ast

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


def revalidations(ports):
    """Name each write of a receipt that the next statement validates again."""
    found = []
    files = sorted(ports.glob('scripts/**/*.py')) + sorted(ports.glob('pkgsrc/*/*/files/**/*.py'))
    for path in files:
        text = path.read_text(errors='replace')
        if 'write_prepared_tree_receipt' not in text:
            continue
        for node in ast.walk(ast.parse(text, str(path))):
            body = getattr(node, 'body', None)
            if not isinstance(body, list):
                continue
            for first, second in zip(body, body[1:]):
                calls = []
                for statement in (first, second):
                    value = getattr(statement, 'value', None)
                    calls.append(value if isinstance(value, ast.Call) and
                                 isinstance(value.func, ast.Attribute) and value.args else None)
                if (calls[0] is not None and calls[1] is not None and
                        calls[0].func.attr == 'write_prepared_tree_receipt' and
                        calls[1].func.attr == 'validate_prepared_tree' and
                        ast.dump(calls[0].args[0]) == ast.dump(calls[1].args[0])):
                    found.append(f'{path.relative_to(ports)}:{second.lineno}')
    return found


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
    source = work / 'staged/owner'
    populate(source)
    log.write_text('')
    owner = ('import sys; sys.path.insert(0, sys.argv[1]); sys.path.append(sys.argv[2]); '
             'import prepared_receipt; '
             "prepared_receipt.write(sys.argv[3], package='archivers/example', identity={'owner': 'test'})")
    result = subprocess.run([sys.executable, '-B', '-I', '-S', '-c', owner, str(counted / 'src'),
                             str(ports / 'scripts'), str(source)], env=env, stdin=subprocess.DEVNULL,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        fail('scripts/prepared_receipt.py failed: ' + result.stderr.strip())
    if len(log.read_text().splitlines()) != 1:
        fail('scripts/prepared_receipt.py hashed its tree more than once')
    sourceprep.validate_prepared_tree(str(source), package='archivers/example', identity={'owner': 'test'})
    found = revalidations(ports)
    if found:
        fail(f'{len(found)} receipt writers hash the tree again at once: ' + ' '.join(found))
    print('PASS: every receipt writer hashes its tree once and writes a valid receipt')


if __name__ == '__main__':
    main()
