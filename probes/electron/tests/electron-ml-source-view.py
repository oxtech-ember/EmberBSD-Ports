#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify ML sibling activation, projection identity and alias confinement."""
import importlib.util
import hashlib,json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
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
    # The production view remains valid through both origin transaction moves.
    (root/'view').rename(root/'candidate');ml.verify_view(view,source,root/'candidate',identities,sourceprep)
    (root/'candidate').rename(root/'stable');ml.verify_view(view,source,root/'stable',identities,sourceprep)
    (root/'stable').rename(root/'backup');ml.verify_view(view,source,root/'backup',identities,sourceprep)
    (root/'backup').rename(root/'view')
    aliases=[selected/'tflite/src'/relative for relative,_ in ml.ALIASES]
    for link,(_,target) in zip(aliases,ml.ALIASES):
        link.unlink();link.symlink_to(root/'old-view/src/third_party'/target)
    try:ml.verify_view(view,source,root/'view',identities,sourceprep)
    except ValueError:pass
    else:raise AssertionError('normal verifier accepted absolute aliases')
    ml.verify_view(view,source,root/'view',identities,sourceprep,legacy_root=root/'old-view')
    try:ml.migrate_aliases(view,root/'view',root/'wrong')
    except ValueError:pass
    else:raise AssertionError('foreign root accepted')
    ml.migrate_aliases(view,root/'view',root/'old-view')
    ml.verify_view(view,source,root/'view',identities,sourceprep)
    # Idempotent retry permits a verified mixed old/new alias state.
    aliases[0].unlink();aliases[0].symlink_to(root/'old-view/src/third_party'/ml.ALIASES[0][1])
    ml.verify_view(view,source,root/'view',identities,sourceprep,legacy_root=root/'old-view')
    ml.migrate_aliases(view,root/'view',root/'old-view');ml.verify_view(view,source,root/'view',identities,sourceprep)
    # Interrupted migration accepts only the remaining exact old alias.
    for link,(_,target) in zip(aliases,ml.ALIASES):
        link.unlink();link.symlink_to(root/'old-view/src/third_party'/target)
    original_replace=ml.os.replace; count=[0]
    def interrupt(*args,**kwargs):
        count[0]+=1
        if count[0]==2:raise OSError('injected interruption')
        return original_replace(*args,**kwargs)
    try:
        with patch.object(ml.os,'replace',side_effect=interrupt):ml.migrate_aliases(view,root/'view',root/'old-view')
    except OSError:pass
    else:raise AssertionError('migration interruption ignored')
    ml.verify_view(view,source,root/'view',identities,sourceprep,legacy_root=root/'old-view')
    ml.migrate_aliases(view,root/'view',root/'old-view');ml.verify_view(view,source,root/'view',identities,sourceprep)
    # Initial normalization preserves provider targets and does not alter out/config.
    config=root/'configuration.json';config.write_bytes(b'old');out=root/'out';out.mkdir();obj=out/'object';obj.write_bytes(b'keep');stamp=obj.stat().st_mtime_ns;args=out/'args.gn';args.write_bytes(b'old args');args_stamp=args.stat().st_mtime_ns;config_stamp=config.stat().st_mtime_ns
    for link,(_,target) in zip(aliases,ml.ALIASES):
        link.unlink();link.symlink_to(root/'view/src/third_party'/target)
    resolved=[os.path.realpath(link) for link in aliases]
    ml.migrate_aliases(view,root/'view',root/'view')
    assert [os.path.realpath(link) for link in aliases]==resolved
    ml.verify_view(view,source,root/'view',identities,sourceprep)
    assert config.read_bytes()==b'old' and config.stat().st_mtime_ns==config_stamp and obj.read_bytes()==b'keep' and obj.stat().st_mtime_ns==stamp and args.read_bytes()==b'old args' and args.stat().st_mtime_ns==args_stamp
    # A mixed initial state remains rejected by the ordinary verifier.
    aliases[0].unlink();aliases[0].symlink_to(root/'view/src/third_party'/ml.ALIASES[0][1])
    try:ml.verify_view(view,source,root/'view',identities,sourceprep)
    except ValueError:pass
    else:raise AssertionError('mixed initial aliases accepted by ordinary verifier')
    ml.migrate_aliases(view,root/'view',root/'view');ml.verify_view(view,source,root/'view',identities,sourceprep)
    # A real process death after staging must leave only an owned external temp.
    aliases[0].unlink();aliases[0].symlink_to(root/'old-view/src/third_party'/ml.ALIASES[0][1])
    pid=os.fork()
    if pid==0:
        real_symlink=ml.os.symlink
        def die_after_stage(*args,**kwargs):
            real_symlink(*args,**kwargs);os._exit(73)
        ml.os.symlink=die_after_stage
        ml.migrate_aliases(view,root/'view',root/'old-view');os._exit(74)
    _,status=os.waitpid(pid,0);assert os.WIFEXITED(status) and os.WEXITSTATUS(status)==73
    temp=root/'.ml-alias-view-0';assert temp.is_symlink()
    ml.verify_view(view,source,root/'view',identities,sourceprep,legacy_root=root/'old-view')
    ml.migrate_aliases(view,root/'view',root/'old-view');assert not temp.exists() and not temp.is_symlink()
    ml.verify_view(view,source,root/'view',identities,sourceprep)
    # Foreign staging entries are preserved and rejected.
    temp.write_text('foreign')
    try:ml.migrate_aliases(view,root/'view',root/'old-view')
    except ValueError:pass
    else:raise AssertionError('foreign recovery staging accepted')
    assert temp.read_text()=='foreign';temp.unlink()
    # A symlink substituted for an intermediate parent must fail closed.
    parent=selected/'tflite/src/tensorflow'; moved=parent.with_name('tensorflow-real');parent.rename(moved);parent.symlink_to(moved)
    try:
        try:ml.migrate_aliases(view,root/'view',root/'old-view')
        except OSError:pass
        else:raise AssertionError('symlink parent accepted')
    finally:parent.unlink();moved.rename(parent)
    # Prepared component recovery verifies old-tflite at a staged path.
    previous=dict(identities);updated=dict(identities);updated['openxla']='e'*64
    transaction_id=hashlib.sha256(json.dumps({'old':previous,'new':updated},sort_keys=True).encode()).hexdigest()
    stage=root/'.view.ml-components-stage';stage.mkdir();(selected/'tflite').rename(stage/'old-tflite')
    marker=root/'.view.ml-components-migration';marker.write_text(json.dumps({'version':1,'state':'prepared','identity':transaction_id},sort_keys=True)+'\n')
    ml.activate(view,source,root/'view',providers,updated,inventory,sourceprep,
                lambda:ml.verify_view(view,source,root/'view',previous,sourceprep),old_identities=previous)
    identities=updated;ml.verify_view(view,source,root/'view',identities,sourceprep)
    assert not marker.exists() and not stage.exists()
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
