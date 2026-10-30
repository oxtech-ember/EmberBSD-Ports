#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Record the libc component prepared by the common LLVM runtime owner."""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'llvm/files'))
import sdk_source

sdk_source.install_signal_handlers()
_, args = sdk_source.load_sdk(sys.argv[1:])
from emberbsd_sdk import inventory, jsonio, sourceprep
from emberbsd_sdk.errors import SDKError

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime-source', type=Path, required=True)
parser.add_argument('--source', type=Path, required=True)
a = parser.parse_args(args)
try:
    if getattr(sourceprep, 'PREPARED_TREE_API', None) != 1:
        raise ValueError('selected SDK lacks prepared source API 1')
    runtime = a.runtime_source.resolve(strict=True)
    dest = a.source.resolve(strict=True)
    record = jsonio.read_json(runtime / 'llvm-source.json')
    if (not isinstance(record, dict) or record.get('format') != 'emberbsd-llvm-source' or
        type(record.get('version')) is not int or record['version'] not in (1, 2) or
        'libc' not in record.get('components', []) or
        not isinstance(record.get('source'), dict) or not isinstance(record.get('recipe'), dict)):
        raise ValueError('invalid common LLVM runtime source record')
    if inventory.snapshot_tree(str(runtime / 'libc')) != inventory.snapshot_tree(str(dest)):
        raise ValueError('staged LLVM libc differs from the prepared common source')
    identity = {'llvm_version': record['llvm_version'], 'source': record['source'],
                'runtime_recipe_files': record['recipe']['files']}
    stamped = sourceprep.write_prepared_tree_receipt(dest, package='lang/llvm-libc-source', identity=identity)
    # The receipt holds the digest just measured from this tree. Check the
    # written receipt instead of hashing the whole tree a second time.
    receipt = Path(dest) / sourceprep.PREPARED_TREE_RECEIPT
    if receipt.read_bytes() != jsonio.json_bytes(stamped):
        raise ValueError('prepared source receipt differs from the measured record')
except (SDKError, OSError, ValueError, KeyError) as exc:
    sdk_source.exit_error(exc, 'LLVM libc source: ')
