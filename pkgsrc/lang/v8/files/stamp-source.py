#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Record the staged V8 source content using the selected SDK API."""
import argparse
import importlib.util
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'llvm/files'))
import sdk_source

sdk_source.install_signal_handlers()
_, args = sdk_source.load_sdk(sys.argv[1:])
from emberbsd_sdk import sourceprep
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
    identity = {'effective': module.effective_package_identity(root, 'lang/v8', upstream)}
    sourceprep.write_prepared_tree_receipt(a.source, package='lang/v8', identity=identity)
    sourceprep.validate_prepared_tree(a.source, package='lang/v8', identity=identity)
except (SDKError, OSError, ValueError) as exc:
    sdk_source.exit_error(exc, 'V8 package source: ')
