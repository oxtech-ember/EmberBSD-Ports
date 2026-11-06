#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Require owner verification and exact prepared SPIRV-Tools source identity."""
import argparse,importlib.util,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
p=argparse.ArgumentParser();p.add_argument('--sdk-source',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.sdk_source.resolve(strict=True)/'src'))
from emberbsd_sdk import sourceprep
files=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name):
 spec=importlib.util.spec_from_file_location(name,files/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
view=load('protobuf-source-view');ots=load('spirv-source-view');provider=load('spirv-provider')
def require(value,message):
 if not value:raise ValueError(message)
with tempfile.TemporaryDirectory(prefix='spirv-provider-') as tmp:
 root=Path(tmp);source=root/'source';source.mkdir();(source/'ots.cc').write_text('verified')
 record=sourceprep.write_prepared_tree_receipt(str(source),package=ots.PACKAGE,identity={'fixture':'verified'})
 archive=root/'ots.tar.gz';archive.write_bytes(b'archive');patch=root/'patch';patch.write_text('tool')
 o=SimpleNamespace(spirv_source=source,spirv_archive=archive,spirv_patch=patch,ports_source=root,sdk_source=a.sdk_source,git='/selected/git')
 calls=[]
 def capture(command,env):
  calls.append(command);return SimpleNamespace(stdout=json.dumps(record).encode())
 sdk={'sourceprep':sourceprep,'process':SimpleNamespace(capture=capture)};native=SimpleNamespace(tool=lambda name:'/selected/'+name)
 c=SimpleNamespace(require=require,git=lambda path:path,source_environment=lambda env:env,view=view);env={}
 values=provider.select(c,ots,o,sdk,native,env)
 assert values['emberbsd_spirv_source_identity']==str(source.resolve()/sourceprep.PREPARED_TREE_RECEIPT)
 assert 'verify-source' in calls[0] and o.spirv_selection['tree_sha256']==record['tree_sha256']
 original=capture
 sdk['process'].capture=lambda command,env:SimpleNamespace(stdout=json.dumps({**record,'tree_sha256':'0'*64}).encode())
 try:provider.select(c,ots,o,sdk,native,env)
 except ValueError as error:assert 'identity changed' in str(error)
 else:raise AssertionError('foreign owner receipt accepted')
print('PASS: SPIRV-Tools provider binds verified owner and exact prepared payload')
