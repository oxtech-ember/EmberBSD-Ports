#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check SQLite projection migration, retry, integrity and unchanged siblings."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile

files = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files'
def load(name):
    spec = importlib.util.spec_from_file_location(name, files / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
view = load('protobuf-source-view'); sqlite = load('sqlite-source-view')
with tempfile.TemporaryDirectory(prefix='electron-sqlite-view-') as temp:
    root = Path(temp).resolve(); source = root/'source'; destination = root/'view'
    original = source/'third_party/sqlite/src/amalgamation'
    (original/'shell').mkdir(parents=True)
    for name in sqlite.FILES:
        path = ((original.parent/'amalgamation_dev'/name[4:]) if name.startswith('dev/') else original/name)
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text('upstream ' + name)
    (original/'README.md').write_text('upstream wrapper')
    (source/'third_party/sqlite/src/test').mkdir(); (source/'third_party/sqlite/src/test/ossfuzz.c').write_text('vendor')
    common=root/'common'; (common/'test').mkdir(parents=True); (common/'test/ossfuzz.c').write_text('common')
    (source/'third_party/sqlite/BUILD.gn').write_text('build')
    (source/'third_party/other').mkdir()
    third = destination/'src/third_party'; third.mkdir(parents=True)
    (third/'sqlite').symlink_to(source/'third_party/sqlite')
    (third/'other').symlink_to(source/'third_party/other')
    sibling = (third/'other').lstat().st_mtime_ns
    def output(version):
        stage = root/('stage-'+version); (stage/'shell').mkdir(parents=True)
        for name in sqlite.FILES:
            (stage/name).parent.mkdir(parents=True, exist_ok=True)
            (stage/name).write_text(version+' '+name)
        receipt = {'format':'emberbsd-chromium-sqlite','version':1,'identity':{'source':str(common)},
                   'files':{name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sqlite.FILES}}
        raw = (json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
        (stage/'receipt.json').write_bytes(raw)
        final = root/('amalgamation-'+hashlib.sha256(raw).hexdigest()); stage.rename(final)
        return sqlite.selection(view, final)[0]
    first, second = output('first'), output('second')
    expected = hashlib.sha256((Path(first['path'])/'receipt.json').read_bytes()).hexdigest()
    last = hashlib.sha256((Path(first['path'])/sqlite.FILES[-1]).read_bytes()).hexdigest()
    assert first['receipt'] == expected and first['receipt'] != last
    def old():
        assert (third/'sqlite').is_symlink()
    sqlite.activate(view, source, destination, first, None, old)
    sqlite.verify_view(view, source, destination, first)
    assert (third/'sqlite/src/test/ossfuzz.c').read_text() == 'common'
    assert (third/'other').lstat().st_mtime_ns == sibling
    # Simulate interruption after the component swap; retry must restore and reapply.
    saved = sqlite.verify_view
    def fail(*args): raise RuntimeError('interrupted')
    sqlite.verify_view = fail
    try:
        sqlite.activate(view, source, destination, second, first, lambda: saved(view,source,destination,first))
    except RuntimeError: pass
    else: raise AssertionError('interruption did not propagate')
    sqlite.verify_view = saved
    sqlite.activate(view, source, destination, second, first, lambda: saved(view,source,destination,first))
    sqlite.verify_view(view, source, destination, second)
    assert (third/'other').lstat().st_mtime_ns == sibling
    (Path(second['path'])/'sqlite3.c').write_text('tampered')
    try: sqlite.verify_view(view, source, destination, second)
    except (ValueError, RuntimeError): pass
    else: raise AssertionError('tampered amalgamation accepted')
print('PASS: SQLite source view transition, interrupted retry, integrity and sibling mtime')
