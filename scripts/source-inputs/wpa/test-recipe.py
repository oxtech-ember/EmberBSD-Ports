#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the WPA common recipe's source identity and mismatch handling."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument('--sdk-source', required=True)
parser.add_argument('--pkgsrc-export', type=Path, required=True)
parser.add_argument('--work', type=Path, required=True)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location('wpa_source', Path(__file__).with_name('source.py'))
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)
source.load_sdk(['--sdk-source', args.sdk_source])
args.work.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=args.work) as tmp:
    root = Path(tmp)
    package = root / 'net/wpa_supplicant'
    shutil.copytree(args.pkgsrc_export / 'pkgsrc/net/wpa_supplicant', package)
    identity, _ = source.recipe(root)
    assert 'Makefile.common' in identity['recipe']
    common = package / 'Makefile.common'
    makefile = package / 'Makefile'
    original_common, original_makefile = common.read_text(), makefile.read_text()
    for case in ('duplicate-version', 'duplicate-distname', 'duplicate-operator', 'sole-plus', 'sole-default', 'archive-mismatch', 'missing-include', 'commented-include'):
        common.write_text(original_common)
        makefile.write_text(original_makefile)
        if case == 'duplicate-version':
            common.write_text(original_common + '\nWPA_SUPPLICANT_VERSION= 2.12\n')
        elif case == 'duplicate-distname':
            common.write_text(original_common + '\nDISTNAME= wpa_supplicant-1.0\n')
        elif case == 'duplicate-operator':
            common.write_text(original_common + '\nDISTNAME += wpa_supplicant-1.0\n')
        elif case == 'sole-plus':
            common.write_text(original_common.replace('DISTNAME=', 'DISTNAME+='))
        elif case == 'sole-default':
            common.write_text(original_common.replace('DISTNAME=', 'DISTNAME?='))
        elif case == 'archive-mismatch':
            common.write_text(original_common.replace('hostapd-${WPA_SUPPLICANT_VERSION}', 'hostapd-1.0'))
        elif case == 'commented-include':
            makefile.write_text(original_makefile.replace('.include ', '#.include '))
        else:
            makefile.write_text(original_makefile.replace(
                '.include "../../net/wpa_supplicant/Makefile.common"', ''))
        try:
            source.recipe(root)
        except source.SDKError:
            continue
        raise AssertionError(case + ' was accepted')

# Changed current receipts reuse the caller's validated export.
effective = {'api': 3, 'package': source.PACKAGE,
             'effective_package_sha256': 'a' * 64, 'upstream': 'b' * 40}
old = {'effective': effective, 'owner_sha256': 'c' * 64}
tree_sha256 = 'd' * 64
validated_export = Path('/already/validated/pkgsrc')
current_identity = {'export': {'upstream': 'b' * 40}, 'owner_sha256': 'f' * 64}
captured = {}
selector = SimpleNamespace(shared_export=lambda *args: validated_export,
                           current_git_package=lambda *args: False)
source.identity_module = lambda: selector
source.source_identity = lambda git: current_identity
source.jsonio = SimpleNamespace(read_json=lambda path: {'identity': old, 'tree_sha256': tree_sha256})
source.sourceprep = SimpleNamespace(PREPARED_TREE_RECEIPT='receipt.json',
                                    validate_prepared_tree=lambda *args, **kwargs:
                                    {'identity': old, 'tree_sha256': tree_sha256})

def capture_prepare(*args, **kwargs):
    captured['exported'] = kwargs.get('exported')
    return {'tree_sha256': tree_sha256}

source.prepare = capture_prepare
source.verify('/prepared/wpa', '/selected/git', '/wpa.tar.gz', '/hostapd.tar.gz',
              '/selected/patch', pkgsrc_export='/already/validated/export')
assert captured.get('exported') == validated_export

# Current package-scoped receipts do not inspect an unrelated export receipt.
current_effective = {'api': 3, 'package': source.PACKAGE,
                   'effective_package_sha256': 'e' * 64, 'upstream': 'b' * 40}
current_current_owner = source.digest(b'current owner')
current_state = {'record': None, 'current': current_effective, 'changed': False}
current_selector = SimpleNamespace(
    git_package_identity=lambda *args: current_state['current'],
    current_git_package=lambda old, owner, current:
        owner == old['owner_sha256'] and old['effective'] == current(),
    shared_export=lambda *args: validated_export,
    equivalent_effective_package=lambda left, right: left == right,
    effective_package_identity=lambda *args: current_state['current'])
source.identity_module = lambda: current_selector
source.read = lambda path: b'current owner'
source.jsonio = SimpleNamespace(read_json=lambda path: current_state['record'])
source.sourceprep = SimpleNamespace(PREPARED_TREE_RECEIPT='receipt.json',
                                    validate_prepared_tree=lambda *args, **kwargs:
                                    current_state['record'])
for owner in (current_current_owner,):
    current = {'effective': current_effective, 'owner_sha256': owner}
    current_record = {'identity': current, 'tree_sha256': tree_sha256}
    current_state['record'] = current_record
    current_state['current'] = current_effective
    current_selector.shared_export = lambda *args: (_ for _ in ()).throw(
        AssertionError('current Git receipt consulted shared export'))
    assert source.verify('/prepared/wpa', '/selected/git',
                         pkgsrc_export='/unrelated-export-without-receipt') == current_record

# A changed package remains on the explicit archive comparison path.
current_state['current'] = dict(current_effective,
                             effective_package_sha256='f' * 64)
current_selector.shared_export = lambda *args: validated_export
current_selector.effective_package_identity = lambda *args: current_state['current']
current_identity = {'export': {'upstream': current_effective['upstream']},
                    'owner_sha256': current_current_owner}
source.source_identity = lambda git: current_identity
current_state['record'] = {'identity': {'effective': current_effective,
                                     'owner_sha256': current_current_owner},
                        'tree_sha256': tree_sha256}
try:
    source.verify('/prepared/wpa', '/selected/git', patch='/selected/patch',
                  pkgsrc_export='/current-export')
except source.SDKError as error:
    assert 'changed wpa_supplicant inputs require an explicit archive' in str(error)
else:
    raise AssertionError('changed WPA package inputs bypassed archive comparison')
print('WPA common recipe boundary PASS')
