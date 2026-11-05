#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify ML sibling activation, projection identity and alias confinement."""
import importlib.util
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(sys.argv[1])/'src'))
from emberbsd_sdk import inventory, sourceprep
owner = Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
view = load('view', owner/'protobuf-source-view.py')
ml = load('ml', owner/'ml-source-view.py')
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); source=root/'source'; origin=source/'third_party'; origin.mkdir(parents=True)
    selected=root/'view/src/third_party'; selected.mkdir(parents=True)
    providers={}; identities={}
    for name in ml.NAMES:
        (origin/name/'src').mkdir(parents=True)
        (origin/name/'BUILD.gn').write_text(name)
        (selected/name).symlink_to(origin/name, target_is_directory=True)
    for name in ml.COMPONENTS.values():
        path=root/'providers'/name; path.mkdir(parents=True); (path/'file').write_text('common-'+name)
        providers[name]=path; identities[name]='a'*64
    (providers['litert']/'tflite').mkdir(); (providers['litert']/'tflite/header.h').write_text('new')
    (origin/'litert/src/tflite').mkdir(); (origin/'litert/src/tflite/header.h').write_text('new')
    for path in ('tensorflow/lite','third_party/xla','third_party/fft2d'):
        (origin/'tflite/src'/path).mkdir(parents=True)
    (origin/'tflite/src/tensorflow/lite/header.h').write_text('old')
    xla=root/'providers/openxla'; xla.mkdir(); (xla/'WORKSPACE').write_text('xla')
    providers['openxla']=xla; identities['openxla']='b'*64
    def old():
        assert all((selected/name).is_symlink() for name in ml.NAMES)
    ml.activate(view, source, root/'view', providers, identities, inventory, sourceprep, old)
    assert (selected/'tflite/src/tensorflow/lite/header.h').read_text() == 'new'
    assert (selected/'tflite/src/third_party/fft2d/file').read_text() == 'common-fft2d'
    assert (selected/'tflite/src/third_party/xla/WORKSPACE').read_text() == 'xla'
    ml.activate(view, source, root/'view', providers, identities, inventory, sourceprep, old)
    unchanged = (selected/'litert').stat().st_ino
    previous = dict(identities)
    (providers['ruy']/'file').write_text('updated-ruy')
    identities['ruy'] = 'c'*64
    ml.activate(view, source, root/'view', providers, identities, inventory, sourceprep,
                lambda: ml.verify_view(view, source, root/'view', previous, sourceprep),
                old_identities=previous)
    assert (selected/'ruy/src/file').read_text() == 'updated-ruy'
    assert (selected/'litert').stat().st_ino == unchanged
    previous = dict(identities)
    siblings = {name: (selected/name).stat().st_ino for name in ml.NAMES if name != 'litert'}
    unchanged_header = (selected/'litert/src/tflite/header.h').stat().st_mtime_ns
    (providers['litert']/'tflite/new-shim.h').write_text('shim')
    identities['litert'] = 'd'*64
    ml.activate(view, source, root/'view', providers, identities, inventory, sourceprep,
                lambda: ml.verify_view(view, source, root/'view', previous, sourceprep),
                old_identities=previous)
    assert (selected/'tflite/src/tensorflow/lite/new-shim.h').read_text() == 'shim'
    assert (selected/'litert/src/tflite/header.h').stat().st_mtime_ns == unchanged_header
    assert all((selected/name).stat().st_ino == inode for name, inode in siblings.items())
    (selected/'ruy/src/file').write_text('foreign')
    try:
        ml.activate(view, source, root/'view', providers, identities, inventory, sourceprep, old,
                    old_identities=identities)
    except Exception:
        pass
    else:
        raise AssertionError('changed projected source accepted')
print('PASS: common ML sibling view, aliases, no-op and changed input refusal')
