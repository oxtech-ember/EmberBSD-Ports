#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Validate cross-export buildlink relocation against both live selections."""
import hashlib
import importlib.util
import json
import os
from unittest.mock import patch
from pathlib import Path
import tempfile

repo = Path(__file__).resolve().parents[3]
script = repo / 'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('controller', script)
controller = importlib.util.module_from_spec(spec); spec.loader.exec_module(controller)
key = 'emberbsd_protobuf_native_prefix'
envkey = 'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='buildlink-root-') as tmp:
    root = Path(tmp).resolve(); work = root/'producer'; work.mkdir()
    target = root/'selected-provider.h'; target.write_text('provider')
    roots=[]; contexts=[]; records=[]; args=[]; env=[]
    for index in range(2):
        export=root/('export'+str(index)); (export/'mk').mkdir(parents=True)
        (export/'mk/bsd.pkg.mk').write_text('framework')
        (export/'mk/pax.mk').write_text('old' if index==0 else 'new')
        (export/'devel/common').mkdir(parents=True)
        (export/'devel/common/buildlink3.mk').write_text('same recipe')
        ctx=work/('host-buildlink-'+str(index)); prefix=ctx/'objects/devel/electron-host-context/work/.buildlink'
        (prefix/'include').mkdir(parents=True); (prefix/'include/selected.h').symlink_to(target)
        (ctx/'make.conf').write_text('WRKOBJDIR= '+str(ctx)+'/objects\nPACKAGES= '+str(ctx)+'/packages\n')
        done=prefix/'.buildlink_selected_done';done.write_text(str(prefix)+'/include/selected.h -> '+str(target)+'\n')
        inputs={str(p):sha(p) for p in (target,export/'mk/pax.mk',export/'devel/common/buildlink3.mk',ctx/'make.conf',done)}
        invocation={'work':str(ctx),'pkgsrc_root':str(export),'host_prefix':str(root/'prefix'),'binding_record':'/selected/binding','shared_image':'yes'}
        record={'identity':{'inputs':inputs,'links':{'include/selected.h':str(target)}},'invocation':invocation}
        (ctx/'selection.json').write_text(json.dumps(record));roots.append(export);contexts.append(ctx);records.append(record)
        args.append({key:str(prefix)});env.append({envkey:str(ctx)})
    def run():return controller.additive_host_buildlink_relocation(args[0],args[1],env[0],env[1],work)
    assert run()=={key}
    candidate=contexts[1]/'selection.json'; original=candidate.read_text()
    def rejected(label, fn):
        try:fn()
        except (ValueError,OSError):pass
        else:raise AssertionError('accepted '+label)
    for label, mutate in (
        ('invocation',lambda r:r['invocation'].update(binding_record='/foreign')),
        ('input set',lambda r:r['identity']['inputs'].pop(str(roots[1]/'devel/common/buildlink3.mk'))),
        ('recorded input hash',lambda r:r['identity']['inputs'].update({str(target):'0'*64})),
        ('link target',lambda r:r['identity']['links'].update({'include/selected.h':str(root/'foreign')})),
        ('root escape',lambda r:r['invocation'].update(pkgsrc_root=str(roots[1]/'..'))),
        ('canonical collision',lambda r:r['identity']['inputs'].update({str(roots[1])+'/mk/../mk/pax.mk':sha(roots[1]/'mk/pax.mk')})),
    ):
        r=json.loads(original);mutate(r);candidate.write_text(json.dumps(r));rejected(label,run)
    candidate.write_text(original)
    alias=root/'export-alias';alias.symlink_to(roots[1],target_is_directory=True)
    r=json.loads(original);r['invocation']['pkgsrc_root']=str(alias);candidate.write_text(json.dumps(r))
    rejected('symlink export root',run);candidate.write_text(original)
    target.write_text('changed');rejected('target bytes',run);target.write_text('provider')
    recipe=roots[1]/'devel/common/buildlink3.mk';recipe.write_text('changed')
    r=json.loads(original);r['identity']['inputs'][str(recipe)]=sha(recipe);candidate.write_text(json.dumps(r))
    rejected('changed current external input',run);recipe.write_text('same recipe');candidate.write_text(original)
    link=contexts[1]/'objects/devel/electron-host-context/work/.buildlink/include/selected.h'
    link.unlink(); link.symlink_to(roots[1]/'mk/pax.mk'); rejected('changed live link',run)
    link.unlink(); link.symlink_to(target)
    extra=link.parent/'unexpected.h'; extra.symlink_to(target); rejected('unrecorded link',run);extra.unlink()
    extra.write_text('unexpected'); rejected('unrecorded view file',run);extra.unlink()
    hidden_dir=link.parent.parent/'empty-subtree'; hidden_dir.mkdir()
    old_hidden=Path(args[0][key])/'empty-subtree'; old_hidden.mkdir()
    real_scandir=os.scandir
    def inaccessible(path):
        if Path(path)==hidden_dir: raise PermissionError('fixture scan failure')
        return real_scandir(path)
    with patch.object(os, 'scandir', side_effect=inaccessible):
        rejected('incomplete view scan',run)
    hidden_dir.rmdir(); old_hidden.rmdir()
    extra_dir=Path(args[1][key])/'extra-directory'; extra_dir.mkdir()
    rejected('directory layout',run);extra_dir.rmdir()
    generated=contexts[1]/'make.conf';before=generated.read_text();generated.write_text(before+'CC= /foreign\n')
    r=json.loads(original);r['identity']['inputs'][str(generated)]=sha(generated);candidate.write_text(json.dumps(r));rejected('wrapper flags',run)
print('PASS: verified buildlink root relocation and negative controls')
