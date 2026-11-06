#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""A changed patch can commit while its ordered inventory stays unchanged."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True, type=Path)
parser.add_argument('--helper', type=Path, default=Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py')
args = parser.parse_args()
sys.path.insert(0, str(args.sdk_source / 'src'))
from emberbsd_sdk import jsonio, paths

spec = importlib.util.spec_from_file_location('refresh', args.helper)
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)
sdk = dict(paths=paths, jsonio=jsonio)

with tempfile.TemporaryDirectory(prefix='refresh-same-cookie-') as directory:
    root = Path(directory).resolve()

    def setup(name):
        work = root / name
        source = work / 'source'
        source.mkdir(parents=True)
        for leaf in ('first', 'second'):
            (source / leaf).write_bytes(b'old\n')
            (source / leaf).chmod(0o644)
        (source / 'compatible.o').write_bytes(b'keep\n')
        inventory = [root / 'patch-meson.build']
        cookie = (str(inventory[0]) + '\n').encode()
        (work / '.patch_done').write_bytes(cookie)
        changes = [(leaf, b'old\n', b'new\n', 0o644, 0o644)
                   for leaf in ('first', 'second')]
        return work, source, inventory, cookie, changes

    # Before commit, ordinary failure rolls back both bytes and timestamps.
    work, source, inventory, cookie, changes = setup('rollback')
    before = (source / 'first').stat().st_mtime_ns
    def fail_before_commit(point):
        if point == 'file-0':
            raise RuntimeError('before commit')
    try:
        refresh.transaction(sdk, work, source, changes, cookie, inventory,
                            lambda: None, inject=fail_before_commit)
    except RuntimeError:
        pass
    else:
        raise AssertionError('pre-commit failure was ignored')
    assert (source / 'first').read_bytes() == b'old\n'
    assert (source / 'first').stat().st_mtime_ns == before
    assert not (work / '.emberbsd-patch-refresh.json').exists()

    # Once invalidation has started, rollback would restore old source while
    # leaving partially invalidated stage metadata. Keep the committed journal.
    work, source, inventory, cookie, changes = setup('clean-failure')
    sibling = (source / 'compatible.o').stat()
    def fail_clean():
        raise RuntimeError('invalidation interrupted')
    try:
        refresh.transaction(sdk, work, source, changes, cookie, inventory, fail_clean)
    except RuntimeError:
        pass
    else:
        raise AssertionError('clean failure was ignored')
    assert (work / '.emberbsd-patch-refresh.json').exists(), 'committed journal was rolled back'
    assert (source / 'first').read_bytes() == b'new\n'
    committed = (source / 'first').stat()
    cleaned = []
    refresh.transaction(sdk, work, source, changes, cookie, inventory,
                        lambda: cleaned.append(True))
    assert cleaned == [True]
    assert (source / 'first').stat().st_mtime_ns == committed.st_mtime_ns
    assert (source / 'compatible.o').stat().st_mtime_ns == sibling.st_mtime_ns
    assert not (work / '.emberbsd-patch-refresh.json').exists()

    # An actual process exit tests durable recovery at each commit boundary.
    for boundary in ('preparing-marker', 'preparing-file-0', 'prepared',
                     'file-0', 'file-1', 'cookie-next', 'cookie',
                     'build-clean', 'complete', 'stage-cleaned'):
        work, source, inventory, cookie, changes = setup('crash-' + boundary)
        sibling = (source / 'compatible.o').stat()
        pid = os.fork()
        if pid == 0:
            def crash(point):
                if point == boundary:
                    os._exit(71)
            refresh.transaction(sdk, work, source, changes, cookie, inventory,
                                lambda: None, inject=crash)
            os._exit(0)
        _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status) == 71, boundary
        refresh.transaction(sdk, work, source, changes, cookie, inventory, lambda: None)
        assert all((source / leaf).read_bytes() == b'new\n' for leaf in ('first', 'second'))
        assert (work / '.patch_done').read_bytes() == cookie
        assert (source / 'compatible.o').stat().st_mtime_ns == sibling.st_mtime_ns
        assert not (work / '.emberbsd-patch-refresh.json').exists()

print('PASS: unchanged patch inventory preserves commit, rollback and crash recovery')
