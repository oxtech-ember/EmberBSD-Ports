#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Record the staged BoringSSL source content using the selected SDK API."""
import argparse
import importlib.util
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'lang/llvm/files'))
import sdk_source

sdk_source.install_signal_handlers()
_, args = sdk_source.load_sdk(sys.argv[1:])
from emberbsd_sdk import jsonio, sourceprep
from emberbsd_sdk.errors import SDKError

parser = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'pkgsrc-root'):
    parser.add_argument('--' + name, required=True)
a = parser.parse_args(args)
try:
    root = Path(a.pkgsrc_root).resolve(strict=True)
    upstream = (root / 'EMBERBSD-PKGSRC-REVISION').read_text().strip()
    module_path = root / 'EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py'
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    identity = {'effective': module.effective_package_identity(root, 'security/boringssl', upstream)}
    stamped = sourceprep.write_prepared_tree_receipt(a.source, package='security/boringssl', identity=identity)
    # The receipt holds the digest just measured from this tree. Check the
    # written receipt instead of hashing the whole tree a second time.
    receipt = Path(a.source) / sourceprep.PREPARED_TREE_RECEIPT
    if receipt.read_bytes() != jsonio.json_bytes(stamped):
        raise ValueError('prepared source receipt differs from the measured record')
except (SDKError, OSError, ValueError) as exc:
    sdk_source.exit_error(exc, 'BoringSSL package source: ')
