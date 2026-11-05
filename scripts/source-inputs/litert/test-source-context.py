#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify LiteRT's extraction limit stays local to its owner context."""
import hashlib
import importlib.util
from pathlib import Path
import sys
from unittest.mock import patch

if len(sys.argv) != 2:
    sys.exit('Usage: test-source-context.py SDK_SOURCE')
root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('litert_source', root / 'source.py')
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
owner.load_sdk(['--sdk-source', sys.argv[1]])
common = Path(owner.tar_archive.__file__).resolve()
ports = root.parents[2]
files = [common, ports / 'scripts/source-inputs/zlib/source.py',
         ports / 'scripts/source-inputs/libpcap/source.py']
before = [hashlib.sha256(path.read_bytes()).digest() for path in files]
original = owner.sourceprep.extract_archive
with patch.object(owner.sourceprep, 'extract_archive') as extract:
    context = owner.source_context()
    context.sourceprep.extract_archive('archive', 'directory', 'root', 'LiteRT')
    assert extract.call_args.kwargs == {'max_bytes': 512 * 1024 * 1024}
    assert context.sourceprep.archive_hashes is owner.sourceprep.archive_hashes
assert owner.sourceprep.extract_archive is original
assert [hashlib.sha256(path.read_bytes()).digest() for path in files] == before
print('PASS: LiteRT extraction limit is local; SDK and shared owners unchanged')
