#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check OTS activation and strict adoption after GN failure."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',owner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp).resolve();work=root/'work';(work/'source-view').mkdir(parents=True);calls=[]
 def verify(*args,**kwargs): calls.append(('verify',tuple(kwargs.get('ml_names',()))));return work/'source-view/src'
 view=SimpleNamespace(verify=verify, _refresh_leaves=lambda *a: verify(), complete_initial=verify)
 ml=SimpleNamespace(NAMES=('litert',),verify_view=lambda *a:None)
 hdr=SimpleNamespace(NAMES=('eigen3',),verify_view=lambda *a:None)
 media=SimpleNamespace(NAMES=('libyuv','libsrtp'),identity=lambda data,name:'a',verify_view=lambda *a:None)
 boring=SimpleNamespace(NAME='boringssl',verify_view=lambda *a:None)
 compression=SimpleNamespace(NAMES=('brotli','zstd'),verify_view=lambda *a:None)
 first={'path':'/first','receipt':'a'};second={'path':'/second','receipt':'b'}
 state={'present':None}
 def ots_verify(*args):
  if state['present'] != args[-2]: raise ValueError('foreign OTS view')
 ots=SimpleNamespace(NAME='ots',verify_view=ots_verify)
 def activate(view,src,dst,new,old,sourceprep,verify_old):
  calls.append(('activate',old,new));verify_old();state['present']=new
 ots.activate=activate
 modules={'electron_boringssl_source_view':boring,'electron_compression_source_view':compression,
          'electron_protobuf_source_view':view,'electron_ml_source_view':ml,
          'electron_header_source_view':hdr,'electron_media_header_view':media,'electron_ots_source_view':ots}
 o=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',
  ml_identities={'litert':'a'},old_ml_identities={'litert':'a'},ml_sources={},ml_sdk={'inventory':object(),'sourceprep':object()},
  ml_headers={'eigen3':{'identity':'a'}},old_header_identities={'eigen3':'a'},media_header_selections={},
  old_media_header_identities={'libyuv':'a','libsrtp':'a'},compression_identity='x',old_compression_identity='x',
  boringssl_identity='b',old_boringssl_identity='b',phase='reconfigure',ots_selection=first)
 def run():
  with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):return m.gn_source(o)
 run();assert ('activate',None,first) in calls and state['present']==first
 (work/'source-view/src/third_party/ots').mkdir(parents=True)
 for phase,flag in (('reconfigure',None),('configure','retry_configure'),('configure','resume_configure')):
  o.phase=phase;o.retry_configure=False;o.resume_configure=False
  if flag:setattr(o,flag,True)
  calls.clear();run();assert not any(row[0]=='activate' for row in calls)
 o.phase='reconfigure';o.retry_configure=False;o.resume_configure=False;o.old_ots_selection=first;o.ots_selection=second
 state['present']=first;calls.clear();run();assert ('activate',first,second) in calls
 # Completed second projection with the old receipt still saved must be adopted.
 state['present']=second;calls.clear();run();assert not any(row[0]=='activate' for row in calls)
 state['present']={'path':'/foreign','receipt':'x'}
 try:run()
 except ValueError:pass
 else:raise AssertionError('foreign completed view accepted')
print('PASS: OTS activation and strict initial/updated GN retry adoption')
