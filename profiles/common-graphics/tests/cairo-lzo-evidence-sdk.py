#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted regression test for the Cairo fuzz adapter.
"""Check that Cairo fuzz evidence binds an SDK commit snapshot.

A later commit in the SDK checkout must not make the recorded SDK inputs
stale. A changed snapshot copy must still fail the SDK's current-input check.
"""

import argparse
import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def git(root, *argv):
    return subprocess.check_output(['git', '-C', str(root), *argv], text=True).strip()


def manifest(fuzz, sdk, work):
    """Return a minimal SDK manifest whose sources are the SDK snapshot."""
    for name in ('clang', 'gcc', 'fuzzer', 'replay', 'build.log', 'corpus/seed'):
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name + '\n', encoding='utf-8')

    def record(name):
        return {'path': str(work / name), 'sha256': fuzz.file_sha256(work / name)}

    sources = [{'name': 'sdk/' + item['path'], 'revision': 'SDK snapshot',
                'path': str(sdk / item['path']), 'sha256': item['sha256']}
               for item in fuzz.tree_files(sdk)]
    return {
        'schema': fuzz.FUZZ_MANIFEST_VERSION,
        'name': 'cairo-lzo-sdk-snapshot-regression',
        'scope': 'diagnostic-host',
        'host': {'system': platform.system(), 'machine': platform.machine()},
        'sources': sources,
        'tools': {'clang': {**record('clang'), 'version': 'clang 23', 'flags': ['-O1']},
                  'gcc': {**record('gcc'), 'version': 'gcc 16.2.0', 'flags': ['-O1']}},
        'binaries': {'fuzzer': record('fuzzer'), 'replay': record('replay')},
        'corpus': {'path': str(work / 'corpus'), 'files': fuzz.tree_files(work / 'corpus')},
        'build_logs': [record('build.log')],
        'limitations': ['Regression fixture without leak detection.'],
        'sanitizer_options': {'ASAN_OPTIONS': 'abort_on_error=1:detect_leaks=0',
                              'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root', type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('cairo_lzo_evidence',
                                                  HERE / 'cairo-lzo-evidence.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)

    with tempfile.TemporaryDirectory(prefix='cairo-lzo-sdk-') as temporary:
        temporary = Path(temporary).resolve()
        checkout = temporary / 'sdk'
        subprocess.check_call(['git', 'clone', '-q', '--no-hardlinks',
                               str(args.sdk_root.resolve(strict=True)), str(checkout)])
        work = temporary / 'work'
        snapshot, revision = adapter.snapshot_sdk(checkout, work / 'sdk-snapshots')
        assert revision == git(checkout, 'rev-parse', 'HEAD')
        assert snapshot == work / 'sdk-snapshots' / revision
        assert checkout not in snapshot.parents
        sys.path.insert(0, str(snapshot / 'src'))
        from emberbsd_sdk import fuzz_check as fuzz
        from emberbsd_sdk.errors import SDKError
        assert Path(fuzz.__file__).resolve() == snapshot / 'src/emberbsd_sdk/fuzz_check.py'

        value = manifest(fuzz, snapshot, work / 'fixture')
        fuzz.validate_manifest(value, current=True)
        # Control: the former checkout-path records go stale on the same change.
        stale = {**value, 'sources': [
            {**source, 'path': str(checkout / source['name'].removeprefix('sdk/'))}
            for source in value['sources']]}
        fuzz.validate_manifest(stale, current=True)

        # A later SDK commit touching process.py must not stale the record.
        process = checkout / 'src/emberbsd_sdk/process.py'
        process.write_text(process.read_text(encoding='utf-8') + '# later commit\n',
                           encoding='utf-8')
        git(checkout, '-c', 'user.name=test', '-c', 'user.email=test@invalid',
            'commit', '-q', '-am', 'later SDK change')
        fuzz.validate_manifest(value, current=True)
        try:
            fuzz.validate_manifest(stale, current=True)
        except SDKError as error:
            assert 'artifact hash mismatch' in str(error), error
        else:
            raise AssertionError('control did not reproduce the stale checkout record')
        assert adapter.snapshot_sdk(checkout, work / 'sdk-snapshots')[1] != revision

        # Reusing the pinned snapshot is exact; the check itself is not weakened.
        git(checkout, 'checkout', '-q', revision)
        assert adapter.snapshot_sdk(checkout, work / 'sdk-snapshots') == (snapshot, revision)
        copied = snapshot / 'src/emberbsd_sdk/process.py'
        os.chmod(copied, 0o644)
        copied.write_text(copied.read_text(encoding='utf-8') + '# altered\n',
                          encoding='utf-8')
        try:
            fuzz.validate_manifest(value, current=True)
        except SDKError as error:
            assert 'artifact hash mismatch' in str(error), error
        else:
            raise AssertionError('altered SDK snapshot passed the current-input check')
        try:
            adapter.snapshot_sdk(checkout, work / 'sdk-snapshots')
        except SystemExit as error:
            assert 'SDK snapshot differs' in str(error), error
        else:
            raise AssertionError('altered SDK snapshot was reused')
    print('PASS cairo-lzo-evidence SDK snapshot')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
