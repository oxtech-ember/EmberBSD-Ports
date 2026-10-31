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
print('WPA common recipe boundary PASS')
