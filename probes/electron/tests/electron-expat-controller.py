#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test codec activation, interrupted recovery, and GN-failure adoption."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',owner); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); work=root/'work'; (work/'source-view').mkdir(parents=True); calls=[]
    def verify(*args, **kwargs):
        calls.append(('verify',tuple(kwargs.get('ml_names',())))); return work/'source-view/src'
    view=SimpleNamespace(verify=verify, _refresh_leaves=lambda *args: calls.append(('verify',tuple(args[3].get('ml_names',())))),
                         complete_initial=lambda *args,**kwargs: calls.append(('verify',tuple(kwargs.get('ml_names',())))))
    ml=SimpleNamespace(NAMES=('litert',),verify_view=lambda *args:None)
    hdr=SimpleNamespace(NAMES=('eigen3',),verify_view=lambda *args:None)
    media=SimpleNamespace(NAMES=('libyuv','libsrtp'),identity=lambda data,name:'a',verify_view=lambda *args:None)
    boring=SimpleNamespace(NAME='boringssl',verify_view=lambda *args:None)
    compression=SimpleNamespace(NAMES=('brotli','zstd'),verify_view=lambda *args:None)
    modules={'electron_boringssl_source_view':boring,'electron_compression_source_view':compression,
             'electron_protobuf_source_view':view,'electron_ml_source_view':ml,
             'electron_header_source_view':hdr,'electron_media_header_view':media}
    o=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',
        ml_identities={'litert':'a'},old_ml_identities={'litert':'a'},ml_sources={},
        ml_sdk={'inventory':object(),'sourceprep':object()},ml_headers={'eigen3':{'identity':'a'}},
        old_header_identities={'eigen3':'a'},media_header_selections={},
        old_media_header_identities={'libyuv':'a','libsrtp':'a'},compression_identity='x',
        old_compression_identity='x',boringssl_identity='b',old_boringssl_identity='b',
        phase='reconfigure', shared_expat=True, shared_codecs=True, old_codec_identity='existing-five')
    def activate(*args,**kwargs):
        assert args[4:] == (('expat',),'expat-components'); calls.append(('activate',)); args[3]()
    compression.activate=activate
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]): m.gn_source(o)
    assert any(c[0]=='activate' for c in calls) and {'expat','dav1d','libaom','libvpx','opus','flac'} <= set(calls[-1][1])
    marker=work/'.source-view.expat-components-migration'; marker.write_text('pending'); calls.clear()
    def recover(*args,**kwargs): marker.unlink(); calls.append(('recover',))
    compression.activate=recover
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]): m.gn_source(o)
    assert calls[0]==('recover',) and {'expat'} <= set(calls[-1][1])
    base=work/'source-view/src/third_party'
    for name in ('expat',): (base/name).mkdir(parents=True)
    def validate(*args):
        if len(args)==4 and args[3]==('expat',):
            assert all((base/n/'valid').is_file() for n in ('expat',)), 'foreign codec view'
    compression.verify_view=validate
    compression.activate=lambda *a,**k: (_ for _ in ()).throw(AssertionError('unexpected activation'))
    for name in ('expat',): (base/name/'valid').write_text('verified')
    for phase,flag in (('reconfigure',None),('configure','resume_configure'),('configure','retry_configure')):
        o.phase=phase; o.retry_configure=False; o.resume_configure=False
        if flag: setattr(o,flag,True)
        calls.clear()
        with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]): m.gn_source(o)
        assert any(c[0]=='verify' and {'expat'} <= set(c[1]) for c in calls)
    (base/'expat/valid').unlink(); o.phase='reconfigure'; o.retry_configure=False
    try:
        with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]): m.gn_source(o)
    except AssertionError as error: assert 'foreign codec view' in str(error)
    else: raise AssertionError('foreign completed XML view accepted')
print('PASS: EXPAT controller activation, recovery and strict retry adoption')
