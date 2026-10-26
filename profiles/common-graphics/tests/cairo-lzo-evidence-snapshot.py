#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted regression test for the Cairo fuzz adapter.
"""Check that Cairo fuzz evidence binds SDK and Ports commit snapshots.

Later commits in the SDK or Ports checkout must not make the recorded inputs
stale. A changed snapshot copy must still fail the SDK's current-input check.
"""

import argparse
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PORTS = HERE.parents[2]
IDENTITY = ('-c', 'user.name=test', '-c', 'user.email=test@invalid')


def git(root, *argv):
    return subprocess.check_output(['git', '-C', str(root), *argv], text=True).strip()


def ports_checkout(paths, destination):
    """Create a Ports repository with the recorded paths at their current bytes."""
    for relative in paths:
        source = PORTS / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copyfile(source, target)
    subprocess.check_call(['git', 'init', '-q', str(destination)])
    git(destination, 'add', '--force', '--', *paths)
    git(destination, *IDENTITY, 'commit', '-q', '-m', 'recorded Ports inputs')


def manifest(fuzz, roots, work, replay_family='clang'):
    """Return a minimal SDK manifest whose sources are the snapshots."""
    for name in ('clang', 'production-compiler', 'fuzzer', 'replay', 'build.log', 'corpus/seed'):
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name + '\n', encoding='utf-8')

    def record(name):
        return {'path': str(work / name), 'sha256': fuzz.file_sha256(work / name)}

    sources = [{'name': f'{label}/{item["path"]}', 'revision': label + ' snapshot',
                'path': str(root / item['path']), 'sha256': item['sha256']}
               for label, root in roots.items() for item in fuzz.tree_files(root)]
    return {
        'schema': fuzz.FUZZ_MANIFEST_VERSION,
        'name': 'cairo-lzo-snapshot-regression',
        'scope': 'diagnostic-host',
        'host': {'system': platform.system(), 'machine': platform.machine()},
        'sources': sources,
        'tools': {'clang': {**record('clang'), 'version': 'clang 23', 'flags': ['-O1'], 'family': 'clang'},
                  'replay': {**record('production-compiler'),
                             'version': 'gcc 16.2.0' if replay_family == 'gcc' else 'clang 23',
                             'flags': ['-O1'], 'family': replay_family}},
        'binaries': {'fuzzer': record('fuzzer'), 'replay': record('replay')},
        'corpus': {'path': str(work / 'corpus'), 'files': fuzz.tree_files(work / 'corpus')},
        'build_logs': [record('build.log')],
        'limitations': ['Regression fixture without leak detection.'],
        'sanitizer_options': {'ASAN_OPTIONS': 'abort_on_error=1:detect_leaks=0',
                              'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'},
    }


def rejects(fuzz, error_type, value, message):
    try:
        fuzz.validate_manifest(value, current=True)
    except error_type as error:
        assert 'artifact hash mismatch' in str(error), error
    else:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root', type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('cairo_lzo_evidence',
                                                  HERE / 'cairo-lzo-evidence.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    clang, gcc = Path('/fixture/clang'), Path('/fixture/gcc')
    assert adapter.replay_selection(clang) == ('clang', clang)
    assert adapter.replay_selection(clang, gcc=gcc) == ('gcc', gcc)
    assert adapter.replay_selection(clang, compiler=gcc, family='gcc') == ('gcc', gcc)
    for options in ({'family': 'gcc'}, {'gcc': gcc, 'family': 'clang'},
                    {'compiler': clang, 'gcc': gcc}, {'family': 'auto'}):
        try:
            adapter.replay_selection(clang, **options)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid replay selection was accepted: ' + repr(options))

    with tempfile.TemporaryDirectory(prefix='cairo-lzo-snapshot-') as temporary:
        temporary = Path(temporary).resolve()
        work = temporary / 'work'
        checkouts = {'sdk': temporary / 'sdk', 'ports': temporary / 'ports'}
        subprocess.check_call(['git', 'clone', '-q', '--no-hardlinks',
                               str(args.sdk_root.resolve(strict=True)), str(checkouts['sdk'])])
        ports_checkout(adapter.PORTS_EVIDENCE_PATHS, checkouts['ports'])
        paths = {'sdk': adapter.SDK_FUZZ_CHECK_PATHS, 'ports': adapter.PORTS_EVIDENCE_PATHS}
        later = {'sdk': ('src/emberbsd_sdk/process.py',),
                 'ports': ('profiles/common-graphics/tests/cairo-lzo-fuzz.c',
                           next(str(path.relative_to(checkouts['ports'])) for path in sorted(
                               (checkouts['ports'] / 'pkgsrc/graphics/cairo/patches').iterdir())))}
        snapshots, revisions = {}, {}
        for label, checkout in checkouts.items():
            parent = work / (label + '-snapshots')
            snapshots[label], revisions[label] = adapter.snapshot_commit(
                checkout, paths[label], parent)
            assert revisions[label] == git(checkout, 'rev-parse', 'HEAD')
            assert snapshots[label] == parent / revisions[label]
            assert checkout not in snapshots[label].parents
        sys.path.insert(0, str(snapshots['sdk'] / 'src'))
        from emberbsd_sdk import fuzz_check as fuzz
        from emberbsd_sdk.errors import SDKError
        assert Path(fuzz.__file__).resolve() == snapshots['sdk'] / 'src/emberbsd_sdk/fuzz_check.py'

        value = manifest(fuzz, snapshots, work / 'fixture')
        fuzz.validate_manifest(value, current=True)
        gcc_value = manifest(fuzz, snapshots, work / 'gcc-fixture', 'gcc')
        fuzz.validate_manifest(gcc_value, current=True)
        legacy = dict(gcc_value, schema=1, tools={
            'gcc' if name == 'replay' else name: {key: item for key, item in tool.items() if key != 'family'}
            for name, tool in gcc_value['tools'].items()})
        fuzz.validate_manifest(legacy, current=True)
        for label, checkout in checkouts.items():
            # Control: former checkout-path records go stale on the same change.
            stale = {**value, 'sources': [
                {**source, 'path': str(checkout / source['name'].removeprefix(label + '/'))}
                if source['name'].startswith(label + '/') else source
                for source in value['sources']]}
            fuzz.validate_manifest(stale, current=True)
            for relative in later[label]:
                path = checkout / relative
                path.write_bytes(path.read_bytes() + b'\n/* later commit */\n')
            git(checkout, *IDENTITY, 'commit', '-q', '-am', 'later change')
            fuzz.validate_manifest(value, current=True)
            rejects(fuzz, SDKError, stale, f'{label} control did not reproduce stale records')
            parent = work / (label + '-snapshots')
            assert adapter.snapshot_commit(checkout, paths[label], parent)[1] != revisions[label]
            # Reusing the pinned snapshot is exact; the check itself is not weakened.
            git(checkout, 'checkout', '-q', revisions[label])
            assert adapter.snapshot_commit(checkout, paths[label], parent) == (
                snapshots[label], revisions[label])

        for label, relative in (('sdk', 'src/emberbsd_sdk/process.py'),
                                ('ports', later['ports'][1])):
            copied = snapshots[label] / relative
            original = copied.read_bytes()
            os.chmod(copied, 0o644)
            copied.write_bytes(original + b'# altered\n')
            rejects(fuzz, SDKError, value, f'altered {label} snapshot passed the check')
            try:
                adapter.snapshot_commit(checkouts[label], paths[label],
                                        work / (label + '-snapshots'))
            except SystemExit as error:
                assert 'snapshot differs' in str(error), error
            else:
                raise AssertionError(f'altered {label} snapshot was reused')
            copied.write_bytes(original)
            os.chmod(copied, 0o444)
            fuzz.validate_manifest(value, current=True)
    print('PASS cairo-lzo-evidence SDK and Ports snapshots')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
