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
        phase='reconfigure', shared_pffft=True, shared_expat=True, shared_codecs=True, old_codec_identity='existing-five')
    def activate(*args,**kwargs):
        assert args[4:] in ((('pffft',),'pffft-components'),(('expat',),'expat-components')); calls.append(('activate',args[4][0])); args[3]()
    compression.activate=activate
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]): m.gn_source(o)
    assert {c[1] for c in calls if c[0]=='activate'} == {'pffft','expat'} and {'pffft','expat','dav1d','libaom','libvpx','opus','flac'} <= set(calls[-1][1])
print('PASS: simultaneous PFFFT and Expat migrations preserve prior codec selection')
