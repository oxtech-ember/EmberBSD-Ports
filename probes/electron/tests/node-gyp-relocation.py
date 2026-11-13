#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise byte-exact GYP root migration and refusals."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

module_path = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/node-gyp-relocation.py'
if 'GYP_PROOF_MODULE' in os.environ:
    module_path = Path(os.environ['GYP_PROOF_MODULE'])
spec = importlib.util.spec_from_file_location('gyp_proof', module_path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='gyp-root-proof-') as tmp:
    root = Path(tmp).resolve(); source = root/'gyp-source'; source.mkdir()
    receipt = source/'emberbsd-prepared-source.json'; receipt.write_text('receipt')
    exports = [root/'export-a', root/'export-b']
    files = ('devel/gyp/Makefile', 'devel/gyp/distinfo', 'devel/gyp/files/verify-source.py',
             'devel/gyp/patches/patch-one', 'EMBERBSD-PKGSRC-REVISION',
             'EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py')
    verifier = '''import pathlib,sys\na=sys.argv\nroot=pathlib.Path(a[a.index("--pkgsrc-root")+1])\nsource=pathlib.Path(a[a.index("--source")+1])\nassert (source/"emberbsd-prepared-source.json").read_text()=="receipt"\nassert (root/"EMBERBSD-PKGSRC-REVISION").read_text()=="same"\n'''
    for export in exports:
        for rel in files:
            p=export/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(verifier if rel.endswith('verify-source.py') else 'same')
    def make(export):
        deps=[str(receipt)]+[str(export / f) for f in files]
        deps.append(str(export/'devel/gyp/files/verify-source.py'))
        return {'emberbsd_node_configure_inputs':['gyp-source='+str(source),'gyp-pkgsrc='+str(export),'v8-source=/same'],
                'emberbsd_node_configure_dependencies':sorted(deps)}
    old,new=map(make,exports)
    def run(a=old,b=new):return m.verify(a,b,sys.executable,root,dict(os.environ))
    assert run() is True
    controller_path = module_path.with_name('build-electron.py')
    controller_spec = importlib.util.spec_from_file_location('electron_controller', controller_path)
    controller = importlib.util.module_from_spec(controller_spec); controller_spec.loader.exec_module(controller)
    try:
        controller.verified_node_configure_v8_path_change(old, new, '/same')
    except ValueError:
        pass
    else:
        raise AssertionError('old Node identity guard accepted GYP root move')
    assert controller.verified_node_configure_path_change(old, new, '/same', sys.executable, root, dict(os.environ)) is True
    assert controller.verified_node_configure_path_change(old, old, '/same', sys.executable, root, dict(os.environ)) is False
    def reject(fn):
        try: fn()
        except (ValueError,OSError): return
        raise AssertionError('unsafe change accepted')
    bad=copy.deepcopy(new);bad['emberbsd_node_configure_inputs'][2]='v8-source=/foreign';reject(lambda:run(old,bad))
    reject(lambda:controller.verified_node_configure_path_change(old, bad, '/same', sys.executable, root, dict(os.environ)))
    bad=copy.deepcopy(new);bad['emberbsd_node_configure_dependencies'].remove(str(exports[1]/files[0]));reject(lambda:run(old,bad))
    bad=copy.deepcopy(new);bad['emberbsd_node_configure_dependencies'].remove(str(exports[1]/files[2]));reject(lambda:run(old,bad))
    bad=copy.deepcopy(new);bad['emberbsd_node_configure_dependencies'].append('/foreign');reject(lambda:run(old,bad))
    for rel in (files[0], files[2], files[-1], files[-2]):
        f=exports[1]/rel;original=f.read_bytes();f.write_text('changed');reject(run);f.write_bytes(original)
    extra=exports[1]/'devel/gyp/hidden';extra.write_text('new');reject(run);extra.unlink()
    extra.symlink_to(receipt);reject(run);extra.unlink()
    receipt.write_text('tampered')
    try:run()
    except Exception:pass
    else:raise AssertionError('invalid prepared receipt accepted')
print('PASS: GYP root proof and negative cases')
