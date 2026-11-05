#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise additive old-subsequence patch replay without touching a pkgsrc stage."""
import argparse
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk-source', required=True, type=Path)
p.add_argument('--patch', required=True, type=Path)
a = p.parse_args()
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep
assert archive_metadata.ARCHIVE_METADATA_API == 1 and sourceprep.SOURCE_PREPARATION_API == 2
module_path = Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py'
spec = importlib.util.spec_from_file_location('stage_local_patch_refresh', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sdk = dict(paths=paths, sourceprep=sourceprep, archive_metadata=archive_metadata, jsonio=jsonio)
with tempfile.TemporaryDirectory(prefix='pkgsrc-patch-refresh-test-') as temp:
 root = Path(temp)
 recipe = root / 'pkgsrc/multimedia/example'; patches = recipe / 'patches'; patches.mkdir(parents=True)
 work = root / 'work'; work.mkdir()
 archive = root / 'example-1.tar.xz'
 with tarfile.open(archive, 'w:xz') as tar:
  for name, data in [('example-1/first', b'A\n'), ('example-1/second', b'C\n')]:
   item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o640 if name.endswith('/second') else 0o644;tar.addfile(item,io.BytesIO(data))
 old_patch=b'--- first\n+++ first\n@@ -1 +1 @@\n-A\n+B\n'
 add_patch=b'--- second\n+++ second\n@@ -1 +1 @@\n-C\n+D\n'
 (patches/'patch-b').write_bytes(old_patch);(patches/'patch-a').write_bytes(add_patch)
 data=archive.read_bytes()
 archive_lines=(f'BLAKE2s ({archive.name}) = {hashlib.blake2s(data).hexdigest()}\n'
                f'SHA512 ({archive.name}) = {hashlib.sha512(data).hexdigest()}\n'
                f'Size ({archive.name}) = {len(data)} bytes\n')
 line_b=f'SHA1 (patch-b) = {hashlib.sha1(old_patch).hexdigest()}\n'
 line_a=f'SHA1 (patch-a) = {hashlib.sha1(add_patch).hexdigest()}\n'
 old_info=('$NetBSD$\n\n'+archive_lines+line_b).encode()
 (recipe/'Makefile').write_text('# fixture\n');(recipe/'distinfo').write_bytes(('$NetBSD$\n\n'+archive_lines+line_a+line_b).encode())
 (work/'.patch_done').write_text(str(patches/'patch-b')+'\n')
 version=root/'BUILD_VERSION'
 version.write_text('multimedia/example/patches/patch-b: '+hashlib.sha256(old_patch).hexdigest()+'\n'
                    'multimedia/example/distinfo: '+hashlib.sha256(old_info).hexdigest()+'\n')
 # Prepared archives normalize modes, while pkgsrc retains archive modes.
 live_source=work/'example-1';live_source.mkdir();(live_source/'second').write_bytes(b'C\n');(live_source/'second').chmod(0o640)
 scratch=root/'scratch';scratch.mkdir()
 result,cookie,inventory=module.prepare(sdk,recipe,work,archive,'example-1',version,a.patch,
  ['-E','-p0','--batch','--forward','-V','simple','-z','.orig'],scratch)
 assert inventory==['patch-a','patch-b'] and cookie.endswith(b'patch-b\n')
 assert [(n,old,new) for n,old,new,_,_ in result]==[('second',b'C\n',b'D\n')]
 assert result[0][3:] == (0o640,0o640)
 (live_source/'second').chmod(0o750)
 bad=root/'bad-mode';bad.mkdir()
 try: module.prepare(sdk,recipe,work,archive,'example-1',version,a.patch,['-E','-p0','--batch','--forward','-V','simple','-z','.orig'],bad)
 except ValueError as exc: assert 'executable bits differ' in str(exc)
 else: raise AssertionError('changed executable mode accepted')
 (live_source/'second').chmod(0o640)
 # Real leaf transaction: a changed leaf plus an added leaf, without touching siblings.
 live=work/'src';live.mkdir();(live/'second').write_bytes(b'C\n');(live/'second').chmod(0o640);(live/'sibling').write_bytes(b'keep')
 (live/'added-parent').mkdir();sibling=(live/'sibling').stat(); original_second=(live/'second').stat()
 changes=result+[('added-parent/new',None,b'new\n',None,0o644)]
 expected_inventory=[patches/x for x in inventory]
 def fail_file(point):
  if point=='file-1': raise RuntimeError('injected failure')
 try: module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None,inject=fail_file)
 except RuntimeError: pass
 else: raise AssertionError('file failure not propagated')
 assert (live/'second').read_bytes()==b'C\n' and not (live/'added-parent/new').exists()
 assert (live/'second').stat().st_mtime_ns == original_second.st_mtime_ns
 assert (work/'.patch_done').read_bytes()==cookie and not (work/'.emberbsd-patch-refresh.json').exists()
 def fail_clean(): raise RuntimeError('build-clean failed')
 try: module.transaction(sdk,work,live,changes,cookie,expected_inventory,fail_clean)
 except RuntimeError: pass
 else: raise AssertionError('build-clean failure not propagated')
 assert (work/'.emberbsd-patch-refresh.json').exists()
 assert (live/'second').read_bytes()==b'D\n' and (live/'added-parent/new').read_bytes()==b'new\n'
 called=[]
 module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:called.append(True))
 assert called==[True] and not (work/'.emberbsd-patch-refresh.json').exists()
 assert (live/'sibling').stat().st_ino==sibling.st_ino and (live/'sibling').stat().st_mtime_ns==sibling.st_mtime_ns
 # A hard interruption at every commit boundary is recovered from the journal.
 for boundary in ('preparing-marker', 'preparing-file-0', 'prepared', 'file-0', 'file-1', 'cookie-next', 'cookie', 'complete', 'stage-cleaned'):
  (work/'.patch_done').write_bytes(cookie);(live/'second').write_bytes(b'C\n')
  (live/'added-parent/new').unlink(missing_ok=True)
  pid=os.fork()
  if pid==0:
   def crash(point):
    if point==boundary: os._exit(71)
   module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None,inject=crash)
   os._exit(0)
  _,status=os.waitpid(pid,0);assert os.waitstatus_to_exitcode(status)==71
  assert (work/'.emberbsd-patch-refresh.json').exists()
  module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None)
  assert (live/'second').read_bytes()==b'D\n' and (live/'added-parent/new').read_bytes()==b'new\n'
  assert not (work/'.emberbsd-patch-refresh.json').exists()
 # A new target appearing after the first swap is preserved, while the first
 # swap is rolled back; once the conflict is removed the marker is retryable.
 (work/'.patch_done').write_bytes(cookie);(live/'second').write_bytes(b'C\n')
 (live/'added-parent/new').unlink(missing_ok=True)
 def appear(point):
  if point=='file-0': (live/'added-parent/new').write_bytes(b'foreign')
 try: module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None,inject=appear)
 except ValueError as exc: assert 'cannot roll back modified' in str(exc)
 else: raise AssertionError('concurrent new target accepted')
 assert (live/'second').read_bytes()==b'C\n' and (live/'added-parent/new').read_bytes()==b'foreign'
 assert (work/'.emberbsd-patch-refresh.json').exists()
 (live/'added-parent/new').unlink()
 module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None)
 assert (live/'second').read_bytes()==b'D\n' and (live/'added-parent/new').read_bytes()==b'new\n'
 # Restrictive umask must not change recorded modes, including mode-only changes.
 (work/'.patch_done').write_bytes(cookie);(live/'second').write_bytes(b'C\n')
 os.chmod(live/'second',0o755);(live/'added-parent/new').unlink(missing_ok=True)
 mode_changes=[('second',b'C\n',b'C\n',0o755,0o644),('added-parent/new',None,b'new\n',None,0o755)]
 previous_umask=os.umask(0o077)
 try:
  def fail_mode(point):
   if point=='file-1': raise RuntimeError('mode rollback')
  try: module.transaction(sdk,work,live,mode_changes,cookie,expected_inventory,lambda:None,inject=fail_mode)
  except RuntimeError: pass
  else: raise AssertionError('mode rollback failure missing')
  assert (live/'second').stat().st_mode & 0o777 == 0o755
  assert not (live/'added-parent/new').exists()
  module.transaction(sdk,work,live,mode_changes,cookie,expected_inventory,lambda:None)
  assert (live/'second').stat().st_mode & 0o777 == 0o644
  assert (live/'added-parent/new').stat().st_mode & 0o777 == 0o755
 finally: os.umask(previous_umask)
 os.chmod(live/'second',0o640)
 # A hard exit between restore hardlink and replace is recoverable.
 (work/'.patch_done').write_bytes(cookie);(live/'second').write_bytes(b'C\n')
 (live/'added-parent/new').unlink(missing_ok=True)
 pid=os.fork()
 if pid==0:
  def restore_crash(point):
   if point=='file-0': raise RuntimeError('start rollback')
   if point=='restore-link': os._exit(71)
  module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None,inject=restore_crash)
  os._exit(0)
 _,status=os.waitpid(pid,0);assert os.waitstatus_to_exitcode(status)==71
 restore=work/'.emberbsd-patch-refresh/restore-0';assert restore.exists()
 # Replacing the candidate with foreign bytes must neither delete nor accept it.
 restore.unlink();restore.write_bytes(b'foreign')
 try: module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None)
 except ValueError as exc: assert 'foreign patch restore candidate' in str(exc)
 else: raise AssertionError('foreign restore candidate accepted')
 assert restore.read_bytes()==b'foreign'
 restore.unlink()
 module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None)
 assert (live/'second').read_bytes()==b'D\n' and not (work/'.emberbsd-patch-refresh.json').exists()
 # Interrupted rollback cleanup remains recoverable after its stage is removed.
 (work/'.patch_done').write_bytes(cookie);(live/'second').write_bytes(b'C\n')
 (live/'added-parent/new').unlink(missing_ok=True)
 pid=os.fork()
 if pid==0:
  def rollback_crash(point):
   if point=='file-0': raise RuntimeError('start rollback')
   if point=='stage-cleaned': os._exit(71)
  module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None,inject=rollback_crash)
  os._exit(0)
 _,status=os.waitpid(pid,0);assert os.waitstatus_to_exitcode(status)==71
 assert (work/'.emberbsd-patch-refresh.json').exists() and not (work/'.emberbsd-patch-refresh').exists()
 module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None)
 assert (live/'second').read_bytes()==b'D\n' and not (work/'.emberbsd-patch-refresh.json').exists()
 # Foreign/tampered journal is rejected without touching live state.
 (work/'.patch_done').write_bytes(cookie);(live/'second').write_bytes(b'C\n')
 (live/'added-parent/new').unlink(missing_ok=True)
 pid=os.fork()
 if pid==0:
  def crash(point):
   if point=='prepared': os._exit(71)
  module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None,inject=crash)
  os._exit(0)
 _,status=os.waitpid(pid,0);assert os.waitstatus_to_exitcode(status)==71
 marker=work/'.emberbsd-patch-refresh.json';original=marker.read_bytes()
 marker.write_bytes(original.replace(b'"second"',b'"sibling"'))
 try: module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None)
 except ValueError as exc: assert 'leaves changed' in str(exc)
 else: raise AssertionError('tampered journal accepted')
 assert (live/'sibling').read_bytes()==b'keep'
 marker.write_bytes(original)
 module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None)
 # A target that appears before staging is never replaced.
 (work/'.patch_done').write_bytes(cookie);(live/'second').write_bytes(b'C\n')
 try: module.transaction(sdk,work,live,changes,cookie,expected_inventory,lambda:None)
 except ValueError as exc: assert 'live preimage differs' in str(exc)
 else: raise AssertionError('existing new-file collision accepted')
 assert (live/'added-parent/new').read_bytes()==b'new\n'
 (patches/'patch-b').write_bytes(old_patch+b'\n')
 try: module.old_metadata(paths,recipe,work,version)
 except ValueError as exc: assert 'old patch identity changed' in str(exc)
 else: raise AssertionError('tampered prior patch accepted')
print('stage-local additive patch provenance and ordered replay passed')
