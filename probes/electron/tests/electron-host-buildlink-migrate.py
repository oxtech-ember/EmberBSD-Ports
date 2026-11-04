#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Accept only the known legacy selection with identical actual inputs."""
import importlib.util
from pathlib import Path
from copy import deepcopy
import tempfile
import sys

sys.path.insert(0, str(Path(sys.argv[1]) / "src"))
from emberbsd_sdk import jsonio

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('host', owner / '../../pkgsrc/devel/electron44/files/host-buildlink.py')
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
old = {'invocation': {'work': '/same'}, 'identity': {'inputs': {
    '/owner': host.LEGACY_SELECTION_SELF_SHA256, '/revision': 'old-revision',
    '/makefile': 'one', '/binding': 'two', '/package/+CONTENTS': 'three'},
    'links': {'lib/example': '/prefix/lib/example'}}}
new = {'inputs': {'/owner': 'new-script', '/makefile': 'one', '/binding': 'two',
                  '/package/+CONTENTS': 'three'}, 'links': {'lib/example': '/prefix/lib/example'}}
saved = deepcopy(old)
result = host.migrate_legacy_selection(saved, new, saved['invocation'], '/owner', '/revision')
assert result['identity'] == new and saved == old
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary); args = root / 'args.gn'; args.write_text('unchanged')
    leaf = root / 'buildlink-file'; leaf.write_text('selected')
    selection = root / 'selection.json'; jsonio.write_json(selection, old)
    before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (args, leaf)]
    jsonio.write_json(selection, result, exclusive=False)
    assert jsonio.read_json(selection) == result
    assert [(p.read_bytes(), p.stat().st_mtime_ns) for p in (args, leaf)] == before
for field in ('/makefile', '/binding', '/package/+CONTENTS', '/owner', '/revision', 'links'):
    bad = deepcopy(old)
    if field == 'links': bad['identity']['links']['lib/example'] = '/foreign'
    elif field == '/revision': del bad['identity']['inputs'][field]
    else: bad['identity']['inputs'][field] = 'changed'
    snapshot = deepcopy(bad)
    try:
        host.migrate_legacy_selection(bad, new, bad['invocation'], '/owner', '/revision')
    except ValueError:
        assert bad == snapshot
    else:
        raise AssertionError('accepted changed ' + field)
print('PASS: legacy selection migration retains actual input identity')
