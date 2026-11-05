#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the stage-local refresh CLI with a selected bmake fixture."""
import argparse, hashlib, io, json, os, subprocess, sys, tarfile, tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--sdk-source',required=True,type=Path);p.add_argument('--patch',required=True,type=Path);a=p.parse_args()
helper=Path(__file__).resolve().parents[1]/'stage-local-patch-refresh.py'
with tempfile.TemporaryDirectory() as d:
 root=Path(d); recipe=root/'pkgsrc/cat/demo';patches=recipe/'patches';patches.mkdir(parents=True)
 work=root/'work';src=work/'demo-1';src.mkdir(parents=True);(src/'first').write_text('B\n');(src/'second').write_text('C\n');(src/'second').chmod(0o640)
 old=b'--- first\n+++ first\n@@ -1 +1 @@\n-A\n+B\n';new=b'--- second\n+++ second\n@@ -1 +1 @@\n-C\n+D\n'
 (patches/'patch-b').write_bytes(old);(patches/'patch-a').write_bytes(new);(recipe/'Makefile').write_text('# fixture\n')
 archive=root/'demo-1.tar.xz'
 with tarfile.open(archive,'w:xz') as tf:
  for name,data in [('demo-1/first',b'A\n'),('demo-1/second',b'C\n')]:
   entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o644;tf.addfile(entry,io.BytesIO(data))
 data=archive.read_bytes(); lines=(f'BLAKE2s ({archive.name}) = {hashlib.blake2s(data).hexdigest()}\nSHA512 ({archive.name}) = {hashlib.sha512(data).hexdigest()}\nSize ({archive.name}) = {len(data)} bytes\n')
 b=f'SHA1 (patch-b) = {hashlib.sha1(old).hexdigest()}\n';c=f'SHA1 (patch-a) = {hashlib.sha1(new).hexdigest()}\n'
 old_info=('$NetBSD$\n\n'+lines+b).encode();(recipe/'distinfo').write_text('$NetBSD$\n\n'+lines+c+b)
 (work/'.patch_done').write_text(str(patches/'patch-b')+'\n')
 db=root/'sys/usr/pkg/pkgdb/demo-1nb1';db.mkdir(parents=True)
 (db/'+BUILD_VERSION').write_text('cat/demo/patches/patch-b: '+hashlib.sha256(old).hexdigest()+'\ncat/demo/distinfo: '+hashlib.sha256(old_info).hexdigest()+'\n')
 values={'WRKDIR':str(work),'WRKSRC':str(src),'PATCH':str(a.patch),'PATCH_ARGS':f'-d {src} -E -p0 --batch --forward -V simple -z .orig','DISTDIR':str(root),'DIST_SUBDIR':'','DISTFILES':archive.name,'DISTNAME':'demo-1','PKG_DBDIR':'/usr/pkg/pkgdb','CROSS_DESTDIR':str(root/'sys'),'PKGBASE':'demo','PKGVERSION_NOREV':'1','PATCHFILES':'','PATCHDIR':str(patches),'DISTINFO_FILE':str(recipe/'distinfo'),'EXTRACT_ONLY':archive.name,'LOCALPATCHES':'','META_PACKAGE':'','SUBST_CLASSES':'','.MAKE.MAKEFILES':'Makefile'}
 fake=root/'bmake';fake.write_text('#!'+sys.executable+'\nimport json,sys,pathlib\nv='+repr(values)+'\nfor x in sys.argv:\n if x.startswith("VARNAMES="):\n  print("\\n".join(v[n] for n in x[9:].split()));sys.exit(0)\nif "build-clean" in sys.argv:pathlib.Path('+repr(str(root/'clean'))+').write_text("yes")\n');fake.chmod(0o755)
 cmd=[sys.executable,'-B',str(helper),'--sdk-source',str(a.sdk_source),'--bmake',str(fake),'--recipe',str(recipe),'--expected-work',str(work)]
 wrong=subprocess.run(cmd[:-1]+[str(root)],capture_output=True,text=True);assert wrong.returncode and 'differs from locked stage' in wrong.stderr
 original=fake.read_text();fake.write_text(original.replace("'SUBST_CLASSES': ''", "'SUBST_CLASSES': 'rewrite'"))
 blocked=subprocess.run(cmd,capture_output=True,text=True);assert blocked.returncode and 'substitutions require' in blocked.stderr
 assert (src/'second').read_text()=='C\n' and not (root/'clean').exists()
 fake.write_text(original)
 subprocess.run(cmd,check=True);assert (src/'second').read_text()=='D\n' and (src/'second').stat().st_mode & 0o777 == 0o640 and (root/'clean').read_text()=='yes'
 assert (work/'.patch_done').read_text()==str(patches/'patch-a')+'\n'+str(patches/'patch-b')+'\n'
print('stage-local CLI validates locked stage and refreshes selected patch series')
