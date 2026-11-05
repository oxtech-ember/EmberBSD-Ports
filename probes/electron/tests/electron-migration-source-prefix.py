#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Only an intact ordered source prefix is valid for explicit migration."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary).resolve(); (root / 'source-inputs').mkdir(); (root / 'repo').mkdir(); (root / 'src').mkdir()
    revision = ['good']
    bsd = SimpleNamespace(relative=lambda name: 'repo', git_bytes=lambda *args: revision[0].encode())
    source = SimpleNamespace(read_series=lambda *args: ['a', 'b', 'c'], series_record=lambda row: row,
        bsd=bsd, current_file=lambda *args: (None, b'content'), digest=lambda data: 'hash')
    build.local_module = lambda *args: source
    record = {'version': 1, 'patches': ['a', 'b'], 'source_revisions': {'repo': 'good'},
              'paths': {'file': {'after': 'hash'}}}
    receipt = root / 'source-inputs/ports-build-sources.json'
    def check():
        receipt.write_text(json.dumps(record)); return build.verify_source(root, root, '/git', allow_ordered_prefix=True)
    check()
    for bad in (['a', 'changed'], ['b', 'a'], []):
        record['patches'] = bad
        try: check(); raise AssertionError('accepted altered or unordered prefix')
        except ValueError: pass
    record['patches'] = ['a', 'b']; revision[0] = 'foreign'
    try: check(); raise AssertionError('accepted foreign revision')
    except ValueError: pass
    revision[0] = 'good'; receipt.write_text(json.dumps(record))
    try: build.verify_source(root, root, '/git'); raise AssertionError('normal verifier accepted prefix')
    except ValueError: pass
print('PASS: migration accepts only intact ordered prefix with unchanged source')
