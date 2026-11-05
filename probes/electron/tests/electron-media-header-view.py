#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise additive media header projection without changing existing views."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(sys.argv[1])/'src'))
from emberbsd_sdk import inventory, sourceprep
owner = Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
view=load('view',owner/'protobuf-source-view.py'); media=load('media',owner/'media-header-view.py')
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp).resolve(); source=root/'source'; origin=source/'third_party'; origin.mkdir(parents=True)
    selected=root/'view/src/third_party'; selected.mkdir(parents=True); keep=selected/'eigen3'; keep.mkdir();(keep/'unchanged').write_text('preserved')
    before=(keep.stat().st_ino, (keep/'unchanged').stat().st_mtime_ns)
    data={}
    for name, rel in (('libyuv','include/libyuv.h'),('libsrtp','include/srtp2/srtp.h')):
        (origin/name/'include').mkdir(parents=True); (origin/name/'include/old.h').write_text('old')
        (origin/name/'BUILD.gn').write_text('gn'); (selected/name).symlink_to(origin/name,target_is_directory=True)
        f=root/'prefix'/rel; f.parent.mkdir(parents=True,exist_ok=True); f.write_text('new-'+name)
        item={'path':str(f),'md5':hashlib.md5(f.read_bytes()).hexdigest(),'stable':list(inventory.stable_identity(f.stat()))}
        data[name]={'source':{'pkgpath':name},'host':{'header_files':{rel:item},'header_hashes':{rel:'same'}},'target':{'header_files':{rel:item},'header_hashes':{rel:'same'}}}
    def old(): assert all((selected/name).is_symlink() for name in media.NAMES)
    real=media.projection.prepare_selected_projection
    count=[]
    def fail(*args, **kwargs):
        count.append(1)
        if len(count)==2: raise ValueError('injected projection failure')
        return real(*args,**kwargs)
    media.projection.prepare_selected_projection=fail
    try:
        try: media.activate(view,source,root/'view',data,inventory,sourceprep,old)
        except ValueError as e: assert str(e)=='injected projection failure'
        else: raise AssertionError('injected failure accepted')
    finally: media.projection.prepare_selected_projection=real
    assert all((selected/name).is_symlink() for name in media.NAMES)
    media.activate(view,source,root/'view',data,inventory,sourceprep,old)
    assert (selected/'libyuv/include/libyuv.h').read_text()=='new-libyuv'
    assert (selected/'libsrtp/include/srtp.h').read_text()=='new-libsrtp'
    assert (keep.stat().st_ino, (keep/'unchanged').stat().st_mtime_ns)==before
    projected=(selected/'libyuv/include/libyuv.h').stat().st_ino
    media.activate(view,source,root/'view',data,inventory,sourceprep,old)
    assert (selected/'libyuv/include/libyuv.h').stat().st_ino == projected
    ids={n:media.identity(data,n) for n in media.NAMES}
    data['libyuv']['target']['header_files']['include/libyuv.h']['stable'][1] += 1
    assert media.identity(data, 'libyuv') == ids['libyuv']
    media.verify_view(view,source,root/'view',ids,sourceprep)
    marker=root/'.view.media-header-components-migration'; marker.write_text('foreign')
    try: media.activate(view,source,root/'view',data,inventory,sourceprep,old,old_identities=ids)
    except ValueError as e: assert 'unexpected media migration marker' in str(e)
    else: raise AssertionError('foreign media marker accepted')
    assert marker.read_text()=='foreign'
print('PASS: additive media headers preserve existing views and recover staging')
