#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify an old wrapper is queried with its saved provider flags."""
import importlib.util, tempfile
from pathlib import Path
from types import SimpleNamespace
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/host-buildlink.py'
spec=importlib.util.spec_from_file_location('host',owner);host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
with tempfile.TemporaryDirectory(prefix='host-saved-flags-') as td:
 root=Path(td).resolve();prefix=root/'prefix';consumer=root/'consumer';view=root/'view'
 consumer.mkdir();view.mkdir();db=prefix/'pkgdb/old-1';db.mkdir(parents=True)
 for name in ('+CONTENTS','+BUILD_INFO'):(db/name).write_text(name)
 class FakeProcess:
  @staticmethod
  def capture(args,env):
   if args[0]=='make':
    vars=[args[i+1] for i,x in enumerate(args[:-1]) if x=='-V']
    new='EMBERBSD_ELECTRON_SHARED_SNAPPY=yes' in args
    if vars==['.MAKE.MAKEFILES','_BUILDLINK_TREE']:
     return SimpleNamespace(stdout=('\nold'+(' snappy' if new else '')+'\n').encode())
    values={'BUILDLINK_API_DEPENDS.old':'old>=1','BUILDLINK_PREFIX.old':str(prefix),'USE_BUILTIN.old':'no',
            'BUILDLINK_API_DEPENDS.snappy':'snappy>=1','BUILDLINK_PREFIX.snappy':'','USE_BUILTIN.snappy':'no'}
    return SimpleNamespace(stdout=('\n'.join(values[x] for x in vars)+'\n').encode())
   if args[2]=='pkgdb':raise ValueError('new provider has no old wrapper prefix')
   return SimpleNamespace(stdout=b'old-1\n')
 command=['make','EMBERBSD_ELECTRON_SHARED_SNAPPY=yes','wrapper'];saved={'invocation':{}}
 try:host.identity(FakeProcess,command,{},consumer,view,prefix,())
 except ValueError as error:assert 'no old wrapper prefix' in str(error)
 else:raise AssertionError('new flags unexpectedly worked against old wrapper')
 current=host.identity(FakeProcess,host._saved_selection_command(command,saved),{},consumer,view,prefix,())
 assert str(db/'+CONTENTS') in current['inputs'] and str(db/'+BUILD_INFO') in current['inputs']
for bad in ({'invocation':{'shared_unrecognized':'yes'}}, {'invocation':{'shared_snappy':'no'}}):
 try:host._saved_selection_command(command,bad)
 except ValueError:pass
 else:raise AssertionError('invalid saved provider flag accepted')
print('PASS: saved flags prevent querying absent new provider prefix in old wrapper')
