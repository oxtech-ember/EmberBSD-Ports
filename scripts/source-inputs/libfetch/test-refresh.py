#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise libfetch's owner refresh with an isolated prepared payload."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock

parser = argparse.ArgumentParser()
parser.add_argument('--sdk-source', required=True)
parser.add_argument('--git', required=True)
parser.add_argument('--patch', required=True)
args = parser.parse_args()
sys.path.insert(0, str(Path(args.sdk_source) / 'src'))
from emberbsd_sdk import jsonio, sourceprep
from emberbsd_sdk.errors import SDKError

path = Path(__file__).with_name('source.py')
spec = importlib.util.spec_from_file_location('libfetch_refresh_test_owner', path)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
owner.jsonio, owner.sourceprep, owner.SDKError = jsonio, sourceprep, SDKError
help_run = subprocess.run([sys.executable, '-B', str(path), '--sdk-source', args.sdk_source,
                           '--git', args.git, 'refresh-source', '--help'],
                          text=True, capture_output=True, check=True)
assert all(flag in help_run.stdout for flag in ('--source', '--patch', '--pkgsrc-export'))
with tempfile.TemporaryDirectory(prefix='libfetch-refresh-') as tmp:
    source = Path(tmp)/'source'
    source.mkdir()
    payload = source/'fetch.c'
    payload.write_text('original\n')
    old = {'old': 'identity'}
    original = sourceprep.write_prepared_tree_receipt(source, package=owner.PACKAGE, identity=old)
    receipt = source/sourceprep.PREPARED_TREE_RECEIPT
    new = {'owner_sha256': 'a'*64, 'effective': {'package': owner.PACKAGE, 'revision': 'current'}}
    class Identity:
        @staticmethod
        def current_git_package(*_args):
            return False
    def expected(_output, _git, _patch, _shared):
        return {'tree_sha256': original['tree_sha256']}
    stamp = payload.stat().st_mtime_ns
    with mock.patch.object(owner, 'identity', return_value=new), \
         mock.patch.object(owner, 'git_effective_identity', return_value=new['effective']), \
         mock.patch.object(owner, 'identity_module', return_value=Identity()), \
         mock.patch.object(owner, 'prepare', side_effect=expected):
        result = owner.refresh(str(source), args.git, args.patch, '/fixture/export')
        assert result['identity'] == new
        assert result['tree_sha256'] == original['tree_sha256']
        assert payload.read_text() == 'original\n' and payload.stat().st_mtime_ns == stamp
        saved = receipt.read_bytes()
        payload.write_text('changed\n')
        try:
            owner.refresh(str(source), args.git, args.patch, '/fixture/export')
        except SDKError:
            pass
        else:
            raise AssertionError('changed payload accepted')
        assert receipt.read_bytes() == saved
print('libfetch refresh: CLI, payload, identity, mtime and failed verification PASS')
