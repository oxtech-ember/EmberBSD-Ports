#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Prove precise GYP export and Node helper transitions."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

module_path = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/node-configure-relocation.py'
spec = importlib.util.spec_from_file_location('node_proof', module_path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
controller_path = module_path.with_name('build-electron.py')
controller_spec = importlib.util.spec_from_file_location('electron_controller', controller_path)
controller = importlib.util.module_from_spec(controller_spec); controller_spec.loader.exec_module(controller)
I='emberbsd_node_configure_inputs'; D='emberbsd_node_configure_dependencies'; H='emberbsd_node_configure_helper'
with tempfile.TemporaryDirectory(prefix='node-configure-proof-') as tmp:
    root=Path(tmp).resolve();source=root/'gyp-source';source.mkdir()
    receipt=source/'emberbsd-prepared-source.json';receipt.write_text('receipt')
    exports=[root/'export-a',root/'export-b'];owners=[root/'owner-a',root/'owner-b']
    files=('devel/gyp/Makefile','devel/gyp/distinfo','devel/gyp/files/verify-source.py',
           'devel/gyp/patches/patch-one','EMBERBSD-PKGSRC-REVISION',
           'EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py')
    verifier='''import pathlib,sys\na=sys.argv\nroot=pathlib.Path(a[a.index("--pkgsrc-root")+1])\nsource=pathlib.Path(a[a.index("--source")+1])\nassert (source/"emberbsd-prepared-source.json").read_text()=="receipt"\nassert (root/"EMBERBSD-PKGSRC-REVISION").read_text()=="same"\n'''
    for export in exports:
        for rel in files:
            p=export/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(verifier if rel.endswith('verify-source.py') else 'same')
    for owner in owners:
        p=owner/'scripts/source-inputs/node/configure-inputs.py';p.parent.mkdir(parents=True);p.write_text('same helper')
    def make(export,owner):
        helper=owner/'scripts/source-inputs/node/configure-inputs.py'
        deps=[str(receipt),str(helper)]+[str(export/f) for f in files]
        deps.append(str(export/'devel/gyp/files/verify-source.py'))
        return {I:['gyp-source='+str(source),'gyp-pkgsrc='+str(export),'v8-source=/same'],D:sorted(deps),H:str(helper)}
    old=make(exports[0],owners[0]);gyp=make(exports[1],owners[0]);helper=make(exports[0],owners[1]);both=make(exports[1],owners[1])
    def run(a,b,owner):return m.verify(a,b,sys.executable,root,dict(os.environ),owner)
    assert run(old,gyp,owners[0])=={I,D}
    assert run(old,helper,owners[1])=={H,D}
    assert run(old,both,owners[1])=={I,D,H}
    assert controller.verified_node_configure_path_change(old,both,'/same',sys.executable,root,dict(os.environ),owners[1])=={I,D,H}
    assert controller.verified_node_configure_path_change(old,old,'/same',sys.executable,root,dict(os.environ),owners[0])==set()
    def reject(fn):
        try:fn()
        except (ValueError,OSError,KeyError):return
        raise AssertionError('unsafe change accepted')
    reject(lambda:controller.verified_node_configure_v8_path_change(old,both,'/same'))
    reject(lambda:controller.verified_node_configure_v8_path_change(old,helper,'/same'))
    reject(lambda:run(old,both,owners[0]))
    bad=copy.deepcopy(both);bad[I][2]='v8-source=/foreign';reject(lambda:run(old,bad,owners[1]))
    bad=copy.deepcopy(both);bad[D].remove(str(exports[1]/files[0]));reject(lambda:run(old,bad,owners[1]))
    bad=copy.deepcopy(both);bad[D].append('/foreign');reject(lambda:run(old,bad,owners[1]))
    bad=copy.deepcopy(both);bad[D].append(bad[H]);reject(lambda:run(old,bad,owners[1]))
    bad=copy.deepcopy(both);bad[H]=str(owners[1]/'scripts/source-inputs/node/other.py');reject(lambda:run(old,bad,owners[1]))
    bad=copy.deepcopy(both);bad[H]=str(owners[0]/'scripts/source-inputs/node/configure-inputs.py');reject(lambda:run(old,bad,owners[1]))
    h=Path(both[H]);h.write_text('different');reject(lambda:run(old,both,owners[1]));h.write_text('same helper')
    for rel in (files[0],files[2],files[-1],files[-2]):
        f=exports[1]/rel;original=f.read_bytes();f.write_text('changed');reject(lambda:run(old,both,owners[1]));f.write_bytes(original)
    extra=exports[1]/'devel/gyp/hidden';extra.write_text('new');reject(lambda:run(old,both,owners[1]));extra.unlink()
    extra.symlink_to(receipt);reject(lambda:run(old,both,owners[1]));extra.unlink()
    receipt.write_text('tampered')
    try:run(old,both,owners[1])
    except Exception:pass
    else:raise AssertionError('invalid prepared receipt accepted')
print('PASS: exact GYP and Node helper transitions and negative controls')
