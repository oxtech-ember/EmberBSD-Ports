#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check SQLite projection migration, retry, integrity and unchanged siblings."""
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
import tempfile
import argparse, sys
parser = argparse.ArgumentParser(); parser.add_argument('--sdk-source', type=Path, required=True)
args = parser.parse_args(); sys.path.insert(0, str(args.sdk_source.resolve() / 'src'))
from emberbsd_sdk import paths
import importlib.util as _iu
_sp = _iu.spec_from_file_location('stable_fixture', Path(__file__).with_name('stable-read-fixture.py'))
fixture = _iu.module_from_spec(_sp); _sp.loader.exec_module(fixture)

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
        receipt = {'format':'emberbsd-chromium-sqlite','version':1,'identity':{'source':str(common), 'generator_sha256':'b'*64, 'flags':['SQLITE_SAFE']},
                   'files':{name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sqlite.FILES}}
        raw = (json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
        (stage/'receipt.json').write_bytes(raw)
        final = root/('amalgamation-'+hashlib.sha256(raw).hexdigest()); stage.rename(final)
        return sqlite.selection(view, final)[0]
    first, second = output('first'), output('second')
    observed=Path(first['path'])/'receipt.json'; fixture.age(observed)
    sqlite.selection(view, first['path'])
    fixture.race(paths, observed, lambda: sqlite.selection(view, first['path']))
    selected_file=Path(first['path'])/'sqlite3.c'; fixture.age(selected_file)
    sqlite.selection(view, first['path'])
    fixture.race(paths, selected_file, lambda: sqlite.selection(view, first['path']))
    expected = hashlib.sha256((Path(first['path'])/'receipt.json').read_bytes()).hexdigest()
    last = hashlib.sha256((Path(first['path'])/sqlite.FILES[-1]).read_bytes()).hexdigest()
    assert first['receipt'] == expected and first['receipt'] != last
    def old():
        assert (third/'sqlite').is_symlink()
    sqlite.activate(view, source, destination, first, None, old)
    sqlite.verify_view(view, source, destination, first)
    # The interrupted initial projection may use a previous generator while
    # the current owner generated exactly the same payload and policy.
    def variant(mutator):
        stage = root/'candidate-stage'; shutil.copytree(Path(first['path']), stage)
        receipt = json.loads((stage/'receipt.json').read_text())
        receipt['identity']['generator_sha256'] = 'a'*64
        mutator(stage, receipt)
        raw = (json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
        (stage/'receipt.json').write_bytes(raw)
        final = root/('amalgamation-'+hashlib.sha256(raw).hexdigest())
        if final.exists(): shutil.rmtree(stage)
        else: stage.rename(final)
        return sqlite.selection(view, final)[0]
    equiv = variant(lambda stage, receipt: None)
    try: sqlite.verify_view(view, source, destination, equiv)
    except (ValueError, OSError): pass
    else: raise AssertionError('old projection accepted as current')
    assert sqlite.recover_equivalent_initial(view, source, destination, equiv) == first
    def reject(fn):
        try: fn()
        except (ValueError, OSError): pass
        else: raise AssertionError('foreign SQLite recovery accepted')
    changed = variant(lambda stage, receipt: receipt['identity'].update(flags=['SQLITE_OTHER']))
    reject(lambda: sqlite.recover_equivalent_initial(view, source, destination, changed))
    other_common = root/'foreign-common'; (other_common/'test').mkdir(parents=True)
    changed_source = variant(lambda stage, receipt: receipt['identity'].update(source=str(other_common)))
    reject(lambda: sqlite.recover_equivalent_initial(view, source, destination, changed_source))
    def alter_payload(stage, receipt):
        (stage/'sqlite3.c').write_text('different')
        receipt['files']['sqlite3.c'] = hashlib.sha256((stage/'sqlite3.c').read_bytes()).hexdigest()
    changed_payload = variant(alter_payload)
    reject(lambda: sqlite.recover_equivalent_initial(view, source, destination, changed_payload))
    bad_generator = variant(lambda stage, receipt: receipt['identity'].update(generator_sha256='invalid'))
    reject(lambda: sqlite.recover_equivalent_initial(view, source, destination, bad_generator))
    marker = destination.parent / ('.' + destination.name + '.sqlite-components-migration')
    marker.write_text('foreign')
    reject(lambda: sqlite.recover_equivalent_initial(view, source, destination, equiv))
    marker.unlink()
    link = third/'sqlite/src/amalgamation/sqlite3.h'; original_link = os.readlink(link)
    link.unlink(); link.symlink_to(Path(equiv['path'])/'sqlite3.h')
    reject(lambda: sqlite.recover_equivalent_initial(view, source, destination, equiv))
    link.unlink(); link.symlink_to(original_link)
    bad_receipt = Path(equiv['path'])/'receipt.json'; original_bytes = bad_receipt.read_bytes()
    bad_receipt.write_bytes(original_bytes+b' ')
    reject(lambda: sqlite.recover_equivalent_initial(view, source, destination, equiv))
    bad_receipt.write_bytes(original_bytes)
    sqlite.activate(view, source, destination, equiv, first,
                    lambda: sqlite.verify_view(view, source, destination, first))
    sqlite.verify_view(view, source, destination, equiv)
    first = equiv
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
