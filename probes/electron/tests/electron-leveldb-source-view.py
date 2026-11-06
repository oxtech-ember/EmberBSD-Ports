#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check LEVELDB projection, interrupted migration and source integrity."""
import argparse, importlib.util, sys, tempfile
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--sdk-source',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.sdk_source.resolve(strict=True)/'src'))
from emberbsd_sdk import sourceprep
from emberbsd_sdk.errors import SDKError
files=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name):
 spec=importlib.util.spec_from_file_location(name,files/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
view=load('protobuf-source-view');leveldb=load('leveldb-source-view')
with tempfile.TemporaryDirectory(prefix='electron-leveldb-view-') as tmp:
 root=Path(tmp).resolve();source=root/'source';dest=root/'view';origin=source/'third_party/leveldatabase';(origin/'src').mkdir(parents=True)
 (origin/'BUILD.gn').write_text('Chromium GN glue');(origin/'src/vendor').write_text('old')
 (source/'third_party/other').mkdir();third=dest/'src/third_party';third.mkdir(parents=True)
 (third/'leveldatabase').symlink_to(origin,target_is_directory=True);(third/'other').symlink_to(source/'third_party/other',target_is_directory=True)
 sibling=(third/'other').lstat().st_mtime_ns
 def prepared(name):
  path=root/name;(path/'src').mkdir(parents=True);(path/'src/leveldb.cc').write_text(name)
  sourceprep.write_prepared_tree_receipt(str(path),package=leveldb.PACKAGE,identity={'fixture':name})
  return leveldb.selection(view,sourceprep,path)
 first,second=prepared('first'),prepared('second')
 receipt=Path(first['path'])/sourceprep.PREPARED_TREE_RECEIPT
 original_stat=Path.stat;calls=[0]
 def changing_stat(path,*args,**kwargs):
  actual=original_stat(path,*args,**kwargs)
  if path != receipt:return actual
  calls[0]+=1
  fields={name:getattr(actual,name) for name in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns','st_atime_ns')}
  fields['st_atime_ns']+=calls[0]
  return SimpleNamespace(**fields)
 with patch.object(Path,'stat',changing_stat):
  assert leveldb.selection(view,sourceprep,first['path'])==first
 assert calls[0]>=2
 calls[0]=0
 def changing_mtime(path,*args,**kwargs):
  result=changing_stat(path,*args,**kwargs)
  if path==receipt:result.st_mtime_ns+=calls[0]
  return result
 try:
  with patch.object(Path,'stat',changing_mtime):leveldb.selection(view,sourceprep,first['path'])
 except ValueError:pass
 else:raise AssertionError('receipt mtime change accepted')
 original_read=Path.read_bytes;original=original_read(receipt)
 def changing_content(path):
  data=original_read(path)
  if path==receipt:path.write_bytes(data+b' ')
  return data
 try:
  with patch.object(Path,'read_bytes',changing_content):leveldb.selection(view,sourceprep,first['path'])
 except ValueError:pass
 else:raise AssertionError('receipt content change accepted')
 receipt.write_bytes(original)
 leveldb.activate(view,source,dest,first,None,sourceprep,lambda:None)
 leveldb.verify_view(view,source,dest,first,sourceprep)
 assert (third/'leveldatabase/src/src/leveldb.cc').read_text()=='first' and (third/'other').lstat().st_mtime_ns==sibling
 saved=leveldb.verify_view
 leveldb.verify_view=lambda *args: (_ for _ in ()).throw(RuntimeError('interrupted'))
 try:leveldb.activate(view,source,dest,second,first,sourceprep,lambda:saved(view,source,dest,first,sourceprep))
 except RuntimeError:pass
 else:raise AssertionError('interruption ignored')
 leveldb.verify_view=saved
 leveldb.activate(view,source,dest,second,first,sourceprep,lambda:saved(view,source,dest,first,sourceprep))
 leveldb.verify_view(view,source,dest,second,sourceprep)
 assert (third/'leveldatabase/src/src/leveldb.cc').read_text()=='second' and (third/'other').lstat().st_mtime_ns==sibling
 (Path(second['path'])/'src/leveldb.cc').write_text('foreign')
 try:leveldb.verify_view(view,source,dest,second,sourceprep)
 except (ValueError, SDKError):pass
 else:raise AssertionError('changed common LEVELDB payload accepted')
print('PASS: LEVELDB source projection, interrupted retry and payload verification')
