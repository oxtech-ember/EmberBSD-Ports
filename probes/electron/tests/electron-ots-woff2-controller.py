#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import importlib.util,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py';s=importlib.util.spec_from_file_location('electron',owner);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
 root=Path(td);work=root/'work';(work/'source-view').mkdir(parents=True);calls=[]
 def verify(*a,**k):calls.append(('verify',set(k.get('ml_names',()))));return work/'source-view/src'
 view=SimpleNamespace(verify=verify,_refresh_leaves=lambda *a:verify(),complete_initial=verify)
 ml=SimpleNamespace(NAMES=('litert',),verify_view=lambda *a:None);hdr=SimpleNamespace(NAMES=('eigen3',),verify_view=lambda *a:None);media=SimpleNamespace(NAMES=('libyuv','libsrtp'),identity=lambda d,n:'a',verify_view=lambda *a:None);boring=SimpleNamespace(NAME='boringssl',verify_view=lambda *a:None)
 compression=SimpleNamespace(NAMES=('brotli','zstd'),verify_view=lambda *a:None)
 selection={'path':'/selected','tree_sha256':'a','receipt_sha256':'b'}
 def activate_ots(*a): calls.append(('ots',));a[-1]()
 ots=SimpleNamespace(NAME='ots',activate=activate_ots,verify_view=lambda *a:None)
 def activate_woff(*a):assert a[4:]==(('woff2',),'woff2-components');calls.append(('woff2',));a[3]()
 compression.activate=activate_woff
 mods={'electron_boringssl_source_view':boring,'electron_compression_source_view':compression,'electron_protobuf_source_view':view,'electron_ml_source_view':ml,'electron_header_source_view':hdr,'electron_media_header_view':media,'electron_ots_source_view':ots}
 o=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',ml_identities={'litert':'a'},old_ml_identities={'litert':'a'},ml_sources={},ml_sdk={'inventory':object(),'sourceprep':object()},ml_headers={'eigen3':{'identity':'a'}},old_header_identities={'eigen3':'a'},media_header_selections={},old_media_header_identities={'libyuv':'a','libsrtp':'a'},compression_identity='x',old_compression_identity='x',boringssl_identity='b',old_boringssl_identity='b',phase='reconfigure',ots_selection=selection,shared_woff2=True)
 with patch.object(m,'local_module',side_effect=lambda name,path:mods[name]):m.gn_source(o)
 assert ('ots',) in calls and ('woff2',) in calls
 assert any(row[0]=='verify' and {'ots','woff2'}<=row[1] for row in calls)
 calls.clear();ots_marker=work/'.source-view.ots-components-migration';woff_marker=work/'.source-view.woff2-components-migration';ots_marker.write_text('pending');woff_marker.write_text('pending')
 def recover_ots(*a):ots_marker.unlink();calls.append(('ots-recovery',));a[-1]()
 def recover_woff(*a):woff_marker.unlink();calls.append(('woff2-recovery',));a[3]()
 ots.activate=recover_ots;compression.activate=recover_woff
 with patch.object(m,'local_module',side_effect=lambda name,path:mods[name]):m.gn_source(o)
 assert ('ots-recovery',) in calls and ('woff2-recovery',) in calls
 assert any(row[0]=='verify' and {'ots','woff2'}<=row[1] for row in calls)
print('PASS: simultaneous OTS and WOFF2 activation preserves both projections')
