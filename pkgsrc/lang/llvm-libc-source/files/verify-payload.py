#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Verify the bytes of a prepared common LLVM libc component."""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'llvm/files'))
import sdk_source

sdk_source.install_signal_handlers()
_, args = sdk_source.load_sdk(sys.argv[1:])
from emberbsd_sdk import jsonio, sourceprep
from emberbsd_sdk.errors import SDKError

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
a = parser.parse_args(args)
try:
    if getattr(sourceprep, 'PREPARED_TREE_API', None) != 1:
        raise ValueError('selected SDK lacks prepared source API 1')
    receipt = jsonio.read_json(a.source / sourceprep.PREPARED_TREE_RECEIPT)
    identity = receipt.get('identity') if isinstance(receipt, dict) else None
    if not isinstance(identity, dict):
        raise ValueError('invalid LLVM libc source identity')
    record = sourceprep.validate_prepared_tree(a.source, package='lang/llvm-libc-source', identity=identity)
    sys.stdout.buffer.write(jsonio.json_bytes(record))
except (SDKError, OSError, ValueError) as exc:
    sdk_source.exit_error(exc, 'LLVM libc source: ')
