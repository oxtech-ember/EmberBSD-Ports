#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Require minizip nb2 before provider provenance and selection."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

root=Path(__file__).resolve().parents[3]
path=root/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for name in ('Makefile','host-dependencies.mk','runtime-dependencies.mk'):
 text=(root/'pkgsrc/devel/electron44'/name).read_text()
 assert 'minizip-ng>=4.2.2nb2' in text and 'minizip-ng>=4.2.2nb1' not in text
with tempfile.TemporaryDirectory(prefix='electron-minizip-floor-') as tmp:
 base=Path(tmp).resolve();host=base/'host';host.mkdir();buildlink=base/'link';(buildlink/'lib/pkgconfig').mkdir(parents=True)
 (buildlink/'lib/pkgconfig/zlib.pc').write_text('fixture')
 work=base/'selection';work.mkdir();(work/'selection.json').write_text(json.dumps({'identity':{'inputs':{str(host/'lib/pkgconfig/zlib.pc'):'ok'}}}))
 def package(role,name,pc):
  p=base/role/name;p.mkdir(parents=True);(p/'+CONTENTS').write_text('lib/pkgconfig/'+pc+'.pc\n');return p
 hz=package('h','zlib-1.3.2nb7','zlib');tz=package('t','zlib-1.3.2nb7','zlib')
 sdk={'process':SimpleNamespace(capture=lambda *a,**k:SimpleNamespace(stdout=b'1.3.2\n'))}
 native=SimpleNamespace(tool=lambda name:'/selected/pkg-config')
 def probe(revision):
  hp=package('h','minizip-ng-4.2.2nb'+str(revision),'minizip');tp=package('t','minizip-ng-4.2.2nb'+str(revision),'minizip')
  opts=SimpleNamespace(shared_minizip=True,host_prefix=host,sysroot=base/'sysroot',host_buildlink_pkgsrc=base/'pkgsrc',
   _common_native_packages={'devel/zlib':[hz],'archivers/minizip-ng':[hp]},
   _common_target_packages={'devel/zlib':[tz],'archivers/minizip-ng':[tp]},
   _compression_catalog={'recipes':{'devel/zlib':{},'archivers/minizip-ng':{}}})
  def validate(*args,**kwargs):
   if kwargs['package_path']=='archivers/minizip-ng':raise LookupError('nb2 reached provenance')
  with patch.object(m,'validate_package_source',side_effect=validate):
   return m.common_minizip(opts,sdk,native,{'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(work)},str(buildlink))
 try:probe(1)
 except ValueError as error:assert 'too old' in str(error)
 else:raise AssertionError('nb1 accepted')
 try:probe(2)
 except LookupError as error:assert 'nb2 reached provenance' in str(error)
 else:raise AssertionError('nb2 did not reach provenance')
print('PASS: minizip nb1 rejected, nb2 reaches normal provenance checks')
