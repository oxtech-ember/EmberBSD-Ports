#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Prepared-source refresh dispatch contracts.
"""Run with selected SDK Python: --sdk-source SDK --git GIT --patch PATCH."""
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'git', 'patch'):
    parser.add_argument('--' + name, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(args.sdk_source) / 'src'))
from emberbsd_sdk import sourceprep

for owner in ('openssl', 'gettext', 'mdns', 'dhcpcd'):
    path = root / owner / 'source.py'
    spec = importlib.util.spec_from_file_location('refresh_owner_' + owner, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = getattr(module, 'engine', module)
    package = target.PACKAGE
    # The real CLI must expose all arguments through the standard selector.
    base = [sys.executable, '-B', str(path), '--sdk-source', args.sdk_source,
            '--git', args.git, 'refresh-source']
    help_result = subprocess.run([*base, '--help'], capture_output=True, text=True)
    assert help_result.returncode == 0 and all(k in help_result.stdout for k in
        ('--source', '--archive', '--patch', '--pkgsrc-export')), (owner, help_result.stderr)
    with tempfile.TemporaryDirectory(prefix='refresh-test-') as directory:
        source = Path(directory) / 'source'
        source.mkdir()
        (source / 'payload').write_text('original\n')
        old = {'old': 'identity'}
        initial = sourceprep.write_prepared_tree_receipt(source, package=package, identity=old)
        receipt = source / sourceprep.PREPARED_TREE_RECEIPT
        current = ({'owner_sha256': 'a' * 64}, {'package': package, 'revision': 'current'})
        calls = []
        def verify(path, git, archive, patch, pkgsrc_export=None):
            calls.append((path, git, archive, patch, pkgsrc_export))
            return sourceprep.validate_prepared_tree(path, package=package, identity=old)
        argv = [str(path), '--sdk-source', args.sdk_source, '--git', args.git,
                'refresh-source', '--source', str(source), '--archive', '/fixture/archive',
                '--patch', args.patch, '--pkgsrc-export', '/fixture/export']
        def run():
            output = io.TextIOWrapper(io.BytesIO(), encoding='utf-8')
            with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(output):
                target.main()
        with mock.patch.object(target, 'source_identity', return_value=current[0]), \
             mock.patch.object(target, 'git_effective_identity', return_value=current[1]), \
             mock.patch.object(target, 'verify', side_effect=verify):
            run()
            after = json.loads(receipt.read_text())
            assert after['tree_sha256'] == initial['tree_sha256']
            assert after['identity'] == {'effective': current[1], 'owner_sha256': current[0]['owner_sha256']}
            assert calls == [(str(source), args.git, '/fixture/archive', args.patch, '/fixture/export')]
        # A changed payload must be refused before receipt replacement.
        before = receipt.read_bytes()
        (source / 'payload').write_text('tampered\n')
        def verify_changed(path, git, archive, patch, pkgsrc_export=None):
            return sourceprep.validate_prepared_tree(path, package=package, identity=after['identity'])
        with mock.patch.object(target, 'source_identity', return_value=current[0]), \
             mock.patch.object(target, 'git_effective_identity', return_value=current[1]), \
             mock.patch.object(target, 'verify', side_effect=verify_changed), \
             contextlib.redirect_stderr(io.StringIO()):
            try:
                run()
            except SystemExit as error:
                assert error.code != 0
            else:
                raise AssertionError(owner + ': tampered payload accepted')
        assert receipt.read_bytes() == before
        # Changing recipe identity during verification must not rewrite the receipt.
        (source / 'payload').write_text('original\n')
        changed = {'owner_sha256': 'b' * 64}
        with mock.patch.object(target, 'source_identity', side_effect=[current[0], changed]), \
             mock.patch.object(target, 'git_effective_identity', return_value=current[1]), \
             mock.patch.object(target, 'verify', side_effect=verify_changed), \
             contextlib.redirect_stderr(io.StringIO()):
            try:
                run()
            except SystemExit as error:
                assert error.code != 0
            else:
                raise AssertionError(owner + ': changing identity accepted')
        assert receipt.read_bytes() == before
        # A concurrently replaced receipt must not be overwritten by refresh.
        foreign = dict(after, identity={'foreign': 'writer'})
        def verify_race(path, git, archive, patch, pkgsrc_export=None):
            record = verify_changed(path, git, archive, patch, pkgsrc_export)
            receipt.write_text(json.dumps(foreign))
            return record
        with mock.patch.object(target, 'source_identity', return_value=current[0]), \
             mock.patch.object(target, 'git_effective_identity', return_value=current[1]), \
             mock.patch.object(target, 'verify', side_effect=verify_race), \
             contextlib.redirect_stderr(io.StringIO()):
            try:
                run()
            except SystemExit as error:
                assert error.code != 0
            else:
                raise AssertionError(owner + ': changing receipt accepted')
        assert json.loads(receipt.read_text()) == foreign
    print(owner + ': CLI, payload, identity and receipt checks PASS')
