#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check PDFium font-to-compound activation and post-GN-failure adoption."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp).resolve();work=root/'work';pdf=work/'source-view/src/third_party/pdfium';pdf.mkdir(parents=True)
 state={'compound':False,'old_valid':True,'activate':0,'verify':0,'legacy':0}
 def verify(*args,**kwargs):
  state['verify']+=1
  if kwargs.get('ml_verify'):kwargs['ml_verify']()
  return work/'source-view/src'
 view=SimpleNamespace(verify=verify,_refresh_leaves=lambda *a:verify(*a[:3],**a[3]),complete_initial=lambda *a,**k:verify(*a,**k))
 noop=lambda *a:None
 ml=SimpleNamespace(NAMES=('litert',),verify_view=noop)
 hdr=SimpleNamespace(NAMES=('eigen3',),verify_view=noop)
 media=SimpleNamespace(NAMES=('libyuv','libsrtp'),identity=lambda data,n:'a',verify_view=noop)
 boring=SimpleNamespace(NAME='boringssl',verify_view=noop)
 compression=SimpleNamespace(NAMES=('brotli','zstd'),verify_view=noop)
 def check_compound(*args):
  if not state['compound']:raise ValueError('not compound')
 def activate(view,source,dest,old_table,old_pdf,new_table,new_pdf,old):
  assert old_table==root/'table' and not old_pdf and new_table==old_table and new_pdf
  old();state['compound']=True;state['activate']+=1
 def check_font(*args):
  if not state['old_valid']:raise ValueError('foreign font view')
 def recover_font(view,source,dest,table,old):
  old();state['legacy']+=1;state['old_valid']=True
  (work/'.source-view.font-table-components-migration').unlink()
 font=SimpleNamespace(NAME='pdfium',verify_view=check_font,verify_pdfium=check_compound,activate_pdfium=activate,activate=recover_font)
 modules={'electron_boringssl_source_view':boring,'electron_compression_source_view':compression,
 'electron_protobuf_source_view':view,'electron_ml_source_view':ml,'electron_header_source_view':hdr,
 'electron_media_header_view':media,'electron_font_table_view':font}
 o=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',
  ml_identities={'litert':'a'},old_ml_identities={'litert':'a'},ml_sources={},
  ml_sdk={'inventory':object(),'sourceprep':object()},ml_headers={'eigen3':{'identity':'a'}},
  old_header_identities={'eigen3':'a'},media_header_selections={},old_media_header_identities={'libyuv':'a','libsrtp':'a'},
  compression_identity='x',old_compression_identity='x',boringssl_identity='b',old_boringssl_identity='b',
  phase='reconfigure',old_font_identity='font',shared_font=True,font_table=root/'table',
  shared_pdf_libraries=True,pdf_identity='verified')
 with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(o)
 assert state['activate']==1 and state['compound'] and state['verify']==2,state
 # GN failed before configuration receipt: verify the completed projection and adopt it.
 for phase,flag in (('reconfigure',None),('configure','retry_configure'),('configure','resume_configure')):
  o.phase=phase;o.retry_configure=False;o.resume_configure=False
  if flag:setattr(o,flag,True)
  with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(o)
  assert state['activate']==1
 # Previous GN failed after a verified font-only activation but before its receipt.
 state['compound']=False;state['old_valid']=True;o.old_font_identity=None;o.phase='reconfigure';o.retry_configure=False;o.resume_configure=False
 with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(o)
 assert state['activate']==2 and state['compound']
 # An interrupted legacy font transaction is recovered before adoption checks.
 state['compound']=False;state['old_valid']=False;o.old_font_identity=None
 (work/'.source-view.font-table-components-migration').write_text('pending')
 with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(o)
 assert state['legacy']==1 and state['activate']==3 and state['compound']
 # A foreign projection without an old font selection cannot be adopted.
 state['compound']=False;state['old_valid']=False;o.old_font_identity=None;o.phase='reconfigure';o.retry_configure=False;o.resume_configure=False
 try:
  with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(o)
 except ValueError as error:assert 'foreign font view' in str(error)
 else:raise AssertionError('foreign PDFium projection accepted')
print('PASS: PDFium controller migration, verified retry adoption and foreign rejection')
