#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
import argparse, hashlib, importlib.util, os, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--sdk-source',type=Path,required=True);a=p.parse_args()
sys.argv=[sys.argv[0],'--sdk-source',str(a.sdk_source.resolve())]
spec=importlib.util.spec_from_file_location('sqlite_generator',Path(__file__).with_name('generate-chromium.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec=importlib.util.spec_from_file_location('stable_fixture',Path(__file__).resolve().parents[3]/'probes/electron/tests/stable-read-fixture.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp).resolve(); binary=root/'bin/tclsh';binary.parent.mkdir();binary.write_bytes(b'valid tcl');binary.chmod(0o755)
 db=root/'pkgdb/tcl-9.0';db.mkdir(parents=True);(db/'+BUILD_INFO').write_text('PKGPATH=lang/tcl\n')
 (db/'+CONTENTS').write_text('bin/tclsh\n@comment MD5:'+hashlib.md5(b'valid tcl',usedforsecurity=False).hexdigest()+'\n')
 native=SimpleNamespace(host={'os':'Darwin'},path=str(root/'bin'))
 with patch.object(m.host_prefix,'validate_host_executable'):
  f.age(binary);m.selected_tcl(root,binary,native)
  f.race(m.paths,binary,lambda:m.selected_tcl(root,binary,native))
  binary.write_bytes(b'bad')
  try:m.selected_tcl(root,binary,native)
  except m.SDKError:pass
  else:raise AssertionError('modified Tcl accepted')
print('PASS: Tcl atime, replacement and checksum')
