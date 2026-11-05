#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check codec provider ownership, versions, checksums and both roles."""
import hashlib, importlib.util, json, tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name,file):
 s=importlib.util.spec_from_file_location(name,owner/file); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=load('electron','build-electron.py'); image=load('image','image-provider.py'); codec=load('pdf','pdfium-provider.py')
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp).resolve(); host=root/'host'; target=root/'sysroot/usr/pkg'; view=root/'view'; dbs={'host':{},'target':{}}; inputs={}
 for role,prefix,suffix in (('host',host,'.dylib'),('target',target,'.so')):
  for name,(path,base,minimum,libraries,modules,headers) in codec.PROVIDERS.items():
   pkg=prefix/'pkgdb'/(base+'-'+'.'.join(map(str,minimum[:3]))+'nb'+str(minimum[3]));pkg.mkdir(parents=True);dbs[role][path]=[pkg]
   entries=list(headers)+['lib/pkgconfig/'+m+'.pc' for m in modules]+['lib/'+lib+suffix for lib in libraries]
   contents=[]
   for entry in entries:
    f=prefix/entry;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('owned');contents += [entry,'@comment MD5:'+hashlib.md5(b'owned',usedforsecurity=False).hexdigest()]
    if role=='host' and entry.endswith('.pc'):
     inputs[str(f)]={};v=view/entry;v.parent.mkdir(parents=True,exist_ok=True);v.write_text('selected')
   (pkg/'+CONTENTS').write_text('\n'.join(contents)+'\n')
   for n in ('+BUILD_INFO','+BUILD_VERSION'): (pkg/n).write_text('owned')
 meta=root/'metadata';meta.mkdir();(meta/'selection.json').write_text(json.dumps({'identity':{'inputs':inputs}}))
 o=SimpleNamespace(shared_pdf_libraries=True,host_prefix=host,sysroot=root/'sysroot',host_buildlink_pkgsrc=root/'pkgsrc',_common_native_packages=dbs['host'],_common_target_packages=dbs['target'],_compression_catalog={'recipes':{x[0]:{} for x in codec.PROVIDERS.values()}})
 native=SimpleNamespace(host={'os':'Darwin'},tool=lambda n:'/selected/'+n)
 sdk={'process':SimpleNamespace(capture=lambda command,env:SimpleNamespace(stdout=('1.0\n'*(len(command)-command.index('--modversion')-1)).encode()))}
 env={'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(meta)}
 with patch.object(c,'validate_package_source') as verify:
  v=codec.select(image,c,o,sdk,native,env,view);assert verify.call_count==6 and len(env['EMBERBSD_PDF_SOURCE_SHA256'])==64
  assert len(v['emberbsd_lcms2_host_libraries'])==1 and v['emberbsd_tiff_target_libraries'][0].endswith('.so')
  f=target/'lib/liblcms2.so';f.write_text('altered')
  try:codec.select(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'differs' in str(error)
  else:raise AssertionError('changed image library accepted')
  f.write_text('owned'); old=dbs['target']['graphics/lcms2'];dbs['target']['graphics/lcms2']=[]
  try:codec.select(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'missing or mismatched' in str(error)
  else:raise AssertionError('missing target accepted')
  dbs['target']['graphics/lcms2']=old
  header=host/'include/lcms2.h'; header.write_text('altered')
  try:codec.select(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'differs' in str(error)
  else:raise AssertionError('changed PDFium header accepted')
  header.write_text('owned')
  pc=view/'lib/pkgconfig/libopenjp2.pc';pc.unlink()
  try:codec.select(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'not selected' in str(error)
  else:raise AssertionError('unselected native PDFium pkg-config accepted')
print('PASS: PDFium provider role ownership, checksums and missing dependency rejection')
