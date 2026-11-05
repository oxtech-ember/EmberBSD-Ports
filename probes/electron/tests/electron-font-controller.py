#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise additive font table selection and completed-view recovery."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',owner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);work=root/'work';(work/'source-view/src/third_party').mkdir(parents=True);calls=[]
 view=SimpleNamespace(verify=lambda *a,**k: calls.append(('verify',k.get('ml_names',()))) or work/'source-view/src')
 ml=SimpleNamespace(NAMES=('litert','tflite'),verify_view=lambda *a:None)
 hdr=SimpleNamespace(NAMES=('eigen3','flatbuffers','fp16'),verify_view=lambda *a:None)
 media=SimpleNamespace(NAMES=('libyuv','libsrtp'),identity=lambda data,name:'a',verify_view=lambda *a:None)
 compression=SimpleNamespace(NAMES=('brotli','zstd'),verify_view=lambda *a:None)
 boring=SimpleNamespace(NAME='boringssl',verify_view=lambda *a:None)
 font=SimpleNamespace(NAME='pdfium',verify_view=lambda *a:calls.append(('font-check',)))
 def activate(*args):
  args[4]();calls.append(('font-activate',))
 font.activate=activate
 modules={'electron_protobuf_source_view':view,'electron_ml_source_view':ml,'electron_header_source_view':hdr,
  'electron_media_header_view':media,'electron_compression_source_view':compression,
  'electron_boringssl_source_view':boring,'electron_font_table_view':font}
 opts=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',
  ml_identities={'litert':'a'},old_ml_identities={'litert':'a'},ml_sources={},ml_sdk={'inventory':object(),'sourceprep':object()},
  ml_headers={n:{'identity':'a'} for n in hdr.NAMES},old_header_identities={n:'a' for n in hdr.NAMES},
  media_header_selections={},old_media_header_identities={'libyuv':'a','libsrtp':'a'},
  compression_identity='c',old_compression_identity='c',boringssl_identity='b',old_boringssl_identity='b',
  phase='reconfigure',shared_font=True,font_table=root/'table')
 with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(opts)
 assert ('font-activate',) in calls
 assert any(call[0]=='verify' and 'pdfium' in call[1] for call in calls)
 # A completed but unsaved view is adopted only after its selected table verifies.
 calls.clear();(work/'source-view/src/third_party/pdfium').mkdir()
 font.activate=lambda *a:(_ for _ in ()).throw(AssertionError('unnecessary projection'))
 with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(opts)
 assert ('font-check',) in calls and not any(call[0]=='font-activate' for call in calls)
 # Interrupted projection is recovered before whole-view verification.
 calls.clear();marker=work/'.source-view.font-table-components-migration';marker.write_text('pending')
 def recover(*args):
  marker.unlink();calls.append(('font-recovered',))
 font.activate=recover
 with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(opts)
 assert calls[0]==('font-recovered',) and any(call[0]=='verify' and 'pdfium' in call[1] for call in calls)
print('PASS: additive font projection and verified unsaved-view adoption')
