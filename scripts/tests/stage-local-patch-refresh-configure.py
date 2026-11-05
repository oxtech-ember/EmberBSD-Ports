#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check configured patch refresh preimages, framework SUBST and retry."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source',required=True,type=Path);parser.add_argument('--patch',required=True,type=Path)
a=parser.parse_args()
helper=Path(__file__).resolve().parents[1]/'stage-local-patch-refresh.py'
with tempfile.TemporaryDirectory(prefix='configured-refresh-') as tmp:
 root=Path(tmp).resolve()
 def setup(name, live):
  base=root/name; recipe=base/'pkgsrc/cat/demo';patches=recipe/'patches';patches.mkdir(parents=True)
  work=base/'work';src=work/'demo-1';src.mkdir(parents=True)
  (src/'first').write_text('B\n');(src/'third').write_text('Q\n');(src/'second').write_bytes(live);(src/'sibling.o').write_text('preserve')
  old=b'--- first\n+++ first\n@@ -1 +1 @@\n-A\n+B\n';new=b'--- second\n+++ second\n@@ -1 +1 @@\n-C\n+D @PREFIX@\n'
  (patches/'patch-b').write_bytes(old);(patches/'patch-a').write_bytes(new)
  previous=base/'previous.mk';previous.write_text('old makefile\n');(recipe/'Makefile').write_text('new makefile\n');(recipe/'Makefile.common').write_text('shared include\n')
  archive=base/'demo-1.tar.xz'
  with tarfile.open(archive,'w:xz') as tar:
   for n,data in [('demo-1/first',b'A\n'),('demo-1/second',b'C\n'),('demo-1/third',b'Q\n')]:
    entry=tarfile.TarInfo(n);entry.size=len(data);entry.mode=0o644;tar.addfile(entry,io.BytesIO(data))
  data=archive.read_bytes();lines=(f'BLAKE2s ({archive.name}) = {hashlib.blake2s(data).hexdigest()}\nSHA512 ({archive.name}) = {hashlib.sha512(data).hexdigest()}\nSize ({archive.name}) = {len(data)} bytes\n')
  oldline=f'SHA1 (patch-b) = {hashlib.sha1(old).hexdigest()}\n';newinfo=('$NetBSD$\n\n'+lines+f'SHA1 (patch-a) = {hashlib.sha1(new).hexdigest()}\n'+oldline)
  (recipe/'distinfo').write_text(newinfo);(work/'.patch_done').write_text(str(patches/'patch-b')+'\n')
  db=base/'sys/usr/pkg/pkgdb/demo-1nb1';db.mkdir(parents=True)
  old_info=('$NetBSD$\n\n'+lines+oldline).encode()
  (db/'+BUILD_VERSION').write_text('cat/demo/patches/patch-b: '+hashlib.sha256(old).hexdigest()+'\ncat/demo/distinfo: '+hashlib.sha256(old_info).hexdigest()+'\ncat/demo/Makefile: '+hashlib.sha256(previous.read_bytes()).hexdigest()+'\ncat/demo/Makefile.common: '+hashlib.sha256((recipe/'Makefile.common').read_bytes()).hexdigest()+'\n')
  vals={'WRKDIR':str(work),'WRKSRC':str(src),'PATCH':str(a.patch),'PATCH_ARGS':f'-d {src} -E -p0 --batch --forward -V simple -z .orig','DISTDIR':str(base),'DIST_SUBDIR':'','DISTFILES':archive.name,'DISTNAME':'demo-1','PKG_DBDIR':'/usr/pkg/pkgdb','CROSS_DESTDIR':str(base/'sys'),'PKGBASE':'demo','PKGVERSION_NOREV':'1','PATCHFILES':'','PATCHDIR':str(patches),'DISTINFO_FILE':str(recipe/'distinfo'),'EXTRACT_ONLY':archive.name,'LOCALPATCHES':'','META_PACKAGE':'','SUBST_CLASSES':'rewrite','SUBST_STAGE.rewrite':'pre-configure','SUBST_FILES.rewrite':'second','SUBST_VARS.rewrite':'PREFIX','SUBST_SED.rewrite':'','SUBST_NOOP_OK.rewrite':'no','_SUBST_COOKIE.rewrite':str(work/'.subst_rewrite_done'),'PKG_FAIL_REASON':'','TOUCH':'/selected/touch','FIND':'/selected/find','.MAKE.MAKEFILES':'Makefile Makefile.common'}
  config=base/'vars.json';config.write_text(json.dumps(vals));fake=base/'bmake'
  fake.write_text('''#!'''+sys.executable+'''\nimport json,pathlib,sys\nv=json.loads(pathlib.Path('''+repr(str(config))+''').read_text()); args=sys.argv[1:]; old='-f' in args\nfor x in args:\n if x.startswith('VARNAMES='):\n  names=x[9:].split(); print("\\n".join(('' if old and n=='SUBST_CLASSES' else v[n]) for n in names));sys.exit()\nif 'pre-patch' in args or 'post-patch' in args: sys.exit()\nif 'configure-clean' in args:
 flag=pathlib.Path('''+repr(str(base/'fail-clean'))+''')
 if flag.exists():flag.unlink();sys.exit(8)
 pathlib.Path('''+repr(str(base/'configure-clean'))+''').write_text('clean');sys.exit()\nif 'subst-rewrite' in args:\n d=pathlib.Path(next((x[7:] for x in args if x.startswith('WRKSRC=')),v['WRKSRC'])); c=pathlib.Path(next((x.split('=',1)[1] for x in args if x.startswith('_SUBST_COOKIE.rewrite=')),v['_SUBST_COOKIE.rewrite'])); f=d/'second'; before=f.read_bytes();after=before.replace(b'@PREFIX@',b'/prefix'); allow='SUBST_NOOP_OK.rewrite=yes' in args\n if not c.exists():\n  if before==after and not allow:sys.exit(7)\n  if before!=after:f.write_bytes(after)\n  c.write_text('' if before==after else 'second\\n')\n  flag=pathlib.Path('''+repr(str(base/'fail-subst'))+''')\n  if allow and flag.exists():flag.unlink();sys.exit(9)\n sys.exit()\n''');fake.chmod(0o755)
  cmd=[sys.executable,'-B',str(helper),'--sdk-source',str(a.sdk_source),'--bmake',str(fake),'--recipe',str(recipe),'--expected-work',str(work),'--previous-makefile',str(previous),'--subst-class','rewrite']
  return base,work,src,cmd,previous
 for name, live in [('old',b'C\n'),('already',b'D /prefix\n')]:
  base,work,src,cmd,previous=setup(name,live);st=(src/'second').stat();sibling=(src/'sibling.o').stat()
  subprocess.run(cmd,check=True,capture_output=True,text=True)
  assert (src/'second').read_bytes()==b'D /prefix\n' and (work/'.subst_rewrite_done').is_file()
  assert (base/'configure-clean').is_file() and (src/'sibling.o').stat().st_mtime_ns==sibling.st_mtime_ns
  if name=='already': assert (src/'second').stat().st_mtime_ns==st.st_mtime_ns
 for name,live in [('retry-old',b'C\n'),('retry-already',b'D /prefix\n')]:
  base,work,src,cmd,previous=setup(name,live); before=(src/'second').stat()
  (base/'fail-clean').write_text('fail once')
  failed=subprocess.run(cmd,capture_output=True,text=True)
  assert failed.returncode and (work/'.emberbsd-patch-refresh.json').exists()
  subprocess.run(cmd,check=True,capture_output=True,text=True)
  assert (src/'second').read_bytes()==b'D /prefix\n' and (work/'.subst_rewrite_done').is_file()
  assert not (work/'.emberbsd-patch-refresh.json').exists()
  if name=='retry-already': assert (src/'second').stat().st_mtime_ns==before.st_mtime_ns
 base,work,src,cmd,previous=setup('retry-subst',b'D /prefix\n')
 (base/'fail-subst').write_text('fail after cookie')
 failed=subprocess.run(cmd,capture_output=True,text=True)
 assert failed.returncode and (work/'.emberbsd-patch-refresh.json').exists() and (work/'.subst_rewrite_done').is_file()
 subprocess.run(cmd,check=True,capture_output=True,text=True)
 assert not (work/'.emberbsd-patch-refresh.json').exists()
 for name,live in [('foreign',b'foreign\n'),('partial',b'D @PREFIX@\n')]:
  base,work,src,cmd,previous=setup(name,live);result=subprocess.run(cmd,capture_output=True,text=True)
  assert result.returncode and 'preimage differs' in result.stderr and (src/'second').read_bytes()==live
 # A foreign mixture of old and completed leaves is not a finished projection.
 base,work,src,cmd,previous=setup('mixed',b'D /prefix\n')
 recipe=base/'pkgsrc/cat/demo';patch=recipe/'patches/patch-a'
 extra=b'--- third\n+++ third\n@@ -1 +1 @@\n-Q\n+R @PREFIX@\n'
 patch.write_bytes(patch.read_bytes()+extra)
 info=recipe/'distinfo';rows=info.read_text().splitlines();info.write_text('\n'.join((f'SHA1 (patch-a) = {hashlib.sha1(patch.read_bytes()).hexdigest()}' if x.startswith('SHA1 (patch-a) = ') else x) for x in rows)+'\n')
 import importlib.util
 sys.path.insert(0,str(a.sdk_source/'src'))
 from emberbsd_sdk import archive_metadata,jsonio,paths,sourceprep
 spec=importlib.util.spec_from_file_location('refresh_mixed',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 sdk=dict(paths=paths,jsonio=jsonio,sourceprep=sourceprep,archive_metadata=archive_metadata)
 scratch=base/'scratch';scratch.mkdir()
 def transform(candidate, affected):
  for n in affected:
   f=candidate/n;f.write_bytes(f.read_bytes().replace(b'@PREFIX@',b'/prefix'))
 try:module.prepare(sdk,recipe,work,base/'demo-1.tar.xz','demo-1',base/'sys/usr/pkg/pkgdb/demo-1nb1/+BUILD_VERSION',a.patch,['-E','-p0','--batch','--forward','-V','simple','-z','.orig'],scratch,transform=transform,allow_completed=True)
 except ValueError as exc:assert 'mixed configured patch' in str(exc)
 else:raise AssertionError('mixed old/new preimages accepted')
 base,work,src,cmd,previous=setup('wrong-include',b'C\n')
 (base/'pkgsrc/cat/demo/Makefile.common').write_text('changed hook\n')
 result=subprocess.run(cmd,capture_output=True,text=True);assert result.returncode and 'included recipe input differs' in result.stderr
 base,work,src,cmd,previous=setup('wrong-old',b'C\n');previous.write_text('foreign\n')
 result=subprocess.run(cmd,capture_output=True,text=True);assert result.returncode and 'previous Makefile' in result.stderr
print('PASS: configured refresh accepts exact old/new, preserves adoption mtime and rejects foreign inputs')
# Unchanged hooks are accepted only when they copy timestamps without touching
# files outside WRKSRC; arbitrary commands and unsafe destinations are rejected.
import importlib.util
spec=importlib.util.spec_from_file_location('refresh',helper);refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)
with tempfile.TemporaryDirectory(prefix='refresh-hooks-') as tmp:
 source=Path(tmp).resolve(); touch='/selected/touch';find='/selected/find'
 (source/'configure.ac').write_text('fixture'); (source/'configure').write_text('fixture')
 output=f'{touch} -r {source}/configure.ac {source}/configure\n{find} {source} -name Makefile.in -exec {touch} -r {source}/configure.ac {{}} +\n'
 files,patterns=refresh.validate_timestamp_hooks(output,source,touch,find)
 assert files=={'configure.ac','configure'} and patterns=={'Makefile.in'}
 for bad in (f'{touch} -r {source}/configure.ac /outside\n',f'/bin/sh -c true\n'):
  try:refresh.validate_timestamp_hooks(bad,source,touch,find)
  except ValueError:pass
  else:raise AssertionError('unsupported patch hook accepted')
print('PASS: supported timestamp-only hooks are bounded to the source tree')
