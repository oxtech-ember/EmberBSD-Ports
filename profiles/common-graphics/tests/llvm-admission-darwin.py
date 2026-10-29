#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise sealed Darwin admission refusals against a completed real bundle."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_admission
import llvm_sdk as sdk


def test(args):
    if len(args) != 1:
        raise ValueError('usage: llvm-admission-darwin.py --sdk-source SDK SEALED_BUNDLE')
    original = Path(sdk.existing_directory(args[0]))
    with tempfile.TemporaryDirectory() as temp:
        bundle = Path(temp) / 'bundle'
        shutil.copytree(original, bundle, symlinks=True)
        receipt_path = bundle / 'provenance/receipt.json'
        receipt = json.loads(receipt_path.read_text())
        def reject(reason):
            try:
                llvm_admission.validate(bundle / 'bin/llvm-config.real', receipt['target_build'], receipt['sysroot'], receipt['native_build'], sealed_darwin_bundle=bundle, relocated_installed_prefix=True)
            except ValueError as exc:
                if reason not in str(exc):
                    raise
            else:
                raise AssertionError('admission accepted invalid ' + reason)
        receipt_path.write_text(receipt_path.read_text() + ' ')
        reject('sealed Darwin receipt mismatch')
        receipt['native_darwin_runtime']['library'] = '../../outside'
        receipt_path.write_text(json.dumps(receipt))
        manifest = bundle / 'inputs.sha256'
        lines = manifest.read_text().splitlines(keepends=True)
        manifest.write_text(''.join(sdk.digest(receipt_path) + '  provenance/receipt.json\n' if line.endswith('  provenance/receipt.json\n') else line for line in lines))
        reject('invalid sealed Darwin runtime path')
        receipt['native_darwin_runtime']['library'] = 'native-darwin/lib/' + receipt['native_darwin_runtime']['linker_target']
        receipt_path.write_text(json.dumps(receipt))
        manifest.write_text(''.join(sdk.digest(receipt_path) + '  provenance/receipt.json\n' if line.endswith('  provenance/receipt.json\n') else line for line in lines))
        library = bundle / receipt['native_darwin_runtime']['library']
        library.unlink()
        library.symlink_to(original / receipt['native_darwin_runtime']['library'])
        reject('sealed Darwin runtime escapes bundle')
    print('PASS: receipt drift, invalid path and symlink escape refused')
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(test))
