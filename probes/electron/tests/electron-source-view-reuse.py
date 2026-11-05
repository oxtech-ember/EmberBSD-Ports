#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Only one invocation may reuse a verified source view between transactions."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
path=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def run(*, marker=None, corruption=None, enabled=True, phase="reconfigure", refresh=False, retry=False):
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp);work=root/'work';(work/'source-view/src/third_party').mkdir(parents=True)
  counts={'whole':0,'targeted':[]}; changed={'neighbor':False,'selected':False}
  def verify(*args,**kwargs):
   counts['whole']+=1
   if changed['neighbor']:raise ValueError('foreign neighbor')
   if kwargs.get('ml_verify'):kwargs['ml_verify']()
   return work/'source-view/src'
  view=SimpleNamespace(verify=verify,_refresh_leaves=lambda *a:verify(*a[:3],**a[3]),complete_initial=lambda *a,**k:verify(*a,**k))
  def selected(*args):
   if changed['selected']:raise ValueError('foreign selected tree')
  ml=SimpleNamespace(NAMES=('litert',),verify_view=selected)
  headers=SimpleNamespace(NAMES=('eigen3',),verify_view=selected)
  media=SimpleNamespace(NAMES=('libyuv','libsrtp'),identity=lambda data,name:'a',verify_view=selected)
  boring=SimpleNamespace(NAME='boringssl',verify_view=selected)
  def activate(view,source,dest,old,names=('brotli','zstd'),label='compression-components'):
   if label=='codec-components' and marker:
    (work/('.source-view.'+marker+'-migration')).unlink()
   old();counts['targeted'].append(tuple(names))
   if corruption and len(counts['targeted'])==6:changed[corruption]=True
  compression=SimpleNamespace(NAMES=('brotli','zstd'),verify_view=selected,activate=activate)
  def font_activate(view,source,dest,table,old):
   old();counts['targeted'].append(('pdfium',))
  font=SimpleNamespace(NAME='pdfium',verify_view=selected,activate=font_activate)
  modules={'electron_boringssl_source_view':boring,'electron_compression_source_view':compression,
           'electron_protobuf_source_view':view,'electron_ml_source_view':ml,
           'electron_header_source_view':headers,'electron_media_header_view':media,
           'electron_font_table_view':font}
  o=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',
   ml_identities={'litert':'a'},old_ml_identities={'litert':'a'},ml_sources={},
   ml_sdk={'inventory':object(),'sourceprep':object()},ml_headers={'eigen3':{'identity':'a'}},
   old_header_identities={'eigen3':'a'},media_header_selections={},
   old_media_header_identities={'libyuv':'a','libsrtp':'a'},compression_identity='x',old_compression_identity='x',
   boringssl_identity='b',old_boringssl_identity='b',phase=phase,refresh_source_view=refresh,retry_configure=retry,font_table=root/'table',
   shared_font=enabled,shared_codecs=enabled,shared_image=enabled,shared_xml=enabled,
   shared_minizip=enabled,shared_ffmpeg=enabled)
  if marker:(work/('.source-view.'+marker+'-migration')).write_text('pending')
  with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
   try:m.gn_source(o)
   except ValueError as error:
    if not corruption:raise
    assert 'foreign '+corruption in str(error)
   else:
    if corruption:raise AssertionError('final check accepted corruption')
  return counts

result=run();assert result['whole']==2 and len(result['targeted'])==6,result
result=run(enabled=False);assert result['whole']==1 and not result['targeted'],result
result=run(enabled=False,refresh=True);assert result['whole']==1 and not result['targeted'],result
result=run(refresh=True);assert result['whole']==2 and len(result['targeted'])==6,result
result=run(phase='configure',retry=True);assert result['whole']==12,result
for kind in ('neighbor','selected'):
 result=run(corruption=kind);assert result['whole']==2,result
result=run(marker='codec-components');assert result['whole']>2,result
result=run(marker='other-components');assert result['whole']==12 and len(result['targeted'])==6,result
print('PASS: six transitions use two full checks, detect corruption and preserve recovery path')
