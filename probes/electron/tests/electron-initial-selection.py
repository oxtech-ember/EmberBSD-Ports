#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise gn_source selection callbacks with filesystem-backed sentinel checks."""

import argparse
import importlib.util
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

parser=argparse.ArgumentParser();parser.add_argument('--controller', type=Path);parser.add_argument('--baseline', action='store_true');cli=parser.parse_args()
owner=cli.controller or Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron_initial_selection',owner)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def exercise(*, phase='configure', flag=None, pending=False, fail_create=False, corrupt=None, expected=None):
 with tempfile.TemporaryDirectory(prefix='electron-initial-selection-') as tmp:
  root=Path(tmp); work=root/'work';work.mkdir(); dest=work/'source-view'; calls=[]
  def create(*args,**kwargs):
   calls.append('create')
   if fail_create:raise ValueError('injected create failure')
   (dest/'src').mkdir(parents=True);(dest/'untouched').write_text('valid')
   return dest/'src'
  def verify(*args,**kwargs):
   calls.append('verify')
   if (dest/'untouched').read_text()!='valid':raise ValueError('corrupt untouched')
   for name in kwargs.get('ml_names',()):
    if name in ('cpuinfo','expat') and (dest/name).read_text()!='valid':raise ValueError('corrupt activated '+name)
   cb=kwargs.get('ml_verify')
   if cb:cb()
   return dest/'src'
  view=SimpleNamespace(create=create,verify=verify,complete_initial=verify,_refresh_leaves=lambda *a:verify())
  ml=SimpleNamespace(NAMES=('litert',),verify_view=lambda *a:None,activate=lambda *a,**k:a[7]())
  hdr=SimpleNamespace(NAMES=('eigen3',),verify_view=lambda *a:None,activate=lambda *a,**k:a[6]())
  media=SimpleNamespace(NAMES=('libyuv','libsrtp'),identity=lambda *a:'a',verify_view=lambda *a:None)
  boring=SimpleNamespace(NAME='boringssl',verify_view=lambda *a:None)
  def activate(*args,**kwargs):
   callback,names=args[3],args[4]; callback()
   for name in names:(dest/name).write_text('valid')
   calls.append('activate:'+names[0])
   if names==('cpuinfo',) and corrupt:
    (dest/('untouched' if corrupt=='untouched' else 'expat')).write_text('changed')
  compression=SimpleNamespace(NAMES=('brotli','zstd'),verify_view=lambda *a:None,activate=activate)
  modules={'electron_boringssl_source_view':boring,'electron_compression_source_view':compression,'electron_protobuf_source_view':view,'electron_ml_source_view':ml,'electron_header_source_view':hdr,'electron_media_header_view':media}
  o=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',ml_identities={'litert':'a'},old_ml_identities={'litert':'a'},ml_sources={},ml_sdk={'inventory':object(),'sourceprep':object()},ml_headers={'eigen3':{'identity':'a'}},old_header_identities={'eigen3':'a'},media_header_selections={},old_media_header_identities={'libyuv':'a','libsrtp':'a'},compression_identity='x',old_compression_identity='x',boringssl_identity='b',old_boringssl_identity='b',phase=phase,shared_cpuinfo=True,shared_expat=True)
  if flag:setattr(o,flag,True)
  if phase!='configure' or flag:
   create();calls.clear()
  if pending:(work/('.source-view.other-components-migration' if pending=='generic' else '.source-view.cpuinfo-components-migration')).write_text('pending')
  try:
   with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):m.gn_source(o)
  except Exception as exc:
   if expected is None or expected not in str(exc):raise
  else:
   if expected:raise AssertionError('expected failure '+expected)
  return calls

normal=exercise()
if cli.baseline:
 assert normal.count('verify')>2,normal
 print('PASS: baseline exceeds two full verifies:',normal.count('verify'))
 raise SystemExit(0)
assert normal.count('verify')==2,normal
for corrupt in ('untouched','activated'):
 exercise(corrupt=corrupt,expected='corrupt '+('untouched' if corrupt=='untouched' else 'activated'))
assert exercise(fail_create=True,expected='injected create failure')==['create']
for flag in ('resume_configure','retry_configure'):
 calls=exercise(flag=flag);assert calls.count('verify')>2,(flag,calls)
calls=exercise(flag='retry_configure',pending=True);assert calls.count('verify')>2,('pending',calls)
calls=exercise(pending='generic');assert calls.count('verify')>2,('fresh pending',calls)
print('PASS: initial two full verifies, corruption, create failure and recovery guards')
