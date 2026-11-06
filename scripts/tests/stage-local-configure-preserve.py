#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise configure output identity, failure recovery and safe inventory."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk-source',type=Path,required=True);p.add_argument('--shell',type=Path,required=True)
a=p.parse_args();helper=Path(__file__).resolve().parents[1]/'stage-local-configure-preserve.py'
spec=importlib.util.spec_from_file_location('configure_preserve',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='stage-configure-') as temp:
 root=Path(temp).resolve();work=root/'work';source=work/'source';source.mkdir(parents=True);recipe=root/'recipe';recipe.mkdir()
 (source/'generated').mkdir();same=source/'generated/same.h';changed=source/'generated/changed.h';obj=source/'existing.o'
 same.write_text('same\n');changed.write_text('old\n');obj.write_text('object');(source/'Makefile').write_text('CFLAGS = -O2\n')
 os.utime(same,ns=(1000000000000000000,1000000000000000000));before=same.stat();obj_before=obj.stat()
 status=source/'config.status';status.write_text("printf '%s\\n' 'Configuration files:' ' Makefile generated/same.h generated/changed.h' 'Configuration headers:' 'Configuration commands:'\n")
 cookie=work/'.configure_done';failure=root/'fail';failure.write_text('once')
 fake=root/'bmake';fake.write_text('#!'+sys.executable+'''\nimport pathlib,sys\na=sys.argv[1:];work=pathlib.Path('''+repr(str(work))+''');source=pathlib.Path('''+repr(str(source))+''');cookie=work/'.configure_done'\nif '-V' in a and '${_BLNK_PACKAGES}' in a:print();sys.exit()\nif '-V' in a and '${TOOLS_CROSS_DESTDIR}' in a:print();sys.exit()\nif '-V' in a:print('tool\\n'+str(work)+'\\n'+str(work/'.tools_done'));sys.exit()
if 'show-vars' in a:print(str(work)+'\\n'+str(source)+'\\n'+'''+repr(str(a.shell))+'''+ '\\n'+str(cookie)+'\\nyes\\n'+str(source));sys.exit()\nif 'configure' in a:\n if not cookie.exists():\n  (source/'generated/same.h').write_text('same\\n');(source/'generated/changed.h').write_text('new\\n');cookie.write_text('done')\n  if (work/'change-flags').exists():(source/'Makefile').write_text('CFLAGS = -O2 -pthread\\n')\n  f=pathlib.Path('''+repr(str(failure))+''')\n  if f.exists():f.unlink();sys.exit(9)\n sys.exit()\n''');fake.chmod(0o755)
 cmd=[sys.executable,'-B',str(helper),'--sdk-source',str(a.sdk_source),'--bmake',str(fake),'--recipe',str(recipe),'--expected-work',str(work),'--make-arg','MAKE_JOBS=2','--make-arg','NATIVE_PKG_ADD_CMD=/run/old/pkg_add','--','USE_CROSS_COMPILE=no']
 fresh=list(cmd);fresh[fresh.index('--expected-work')+1]=str(root/'missing-stage')
 subprocess.run(fresh,check=True,capture_output=True,text=True)
 assert not (root/'missing-stage').exists() and not cookie.exists()
 saved_source=work/'saved-source';source.rename(saved_source)
 subprocess.run(cmd,check=True,capture_output=True,text=True)
 assert not source.exists() and not cookie.exists()
 source.symlink_to(work/'dangling-source',target_is_directory=True)
 assert subprocess.run(cmd,capture_output=True,text=True).returncode
 source.unlink();(work/'.emberbsd-configure-preserve.json').write_text('{}')
 assert subprocess.run(cmd,capture_output=True,text=True).returncode
 (work/'.emberbsd-configure-preserve.json').unlink();saved_source.rename(source)
 result=subprocess.run(cmd,capture_output=True,text=True);assert result.returncode and (work/'.emberbsd-configure-preserve.json').is_file()
 marker=work/'.emberbsd-configure-preserve.json'; saved=marker.read_text(); foreign=json.loads(saved)
 foreign['files']['../escape']=next(iter(foreign['files'].values()));marker.write_text(json.dumps(foreign))
 assert subprocess.run(cmd,capture_output=True,text=True).returncode
 marker.write_text(saved)
 retry=['MAKE_JOBS=1' if value=='MAKE_JOBS=2' else 'NATIVE_PKG_ADD_CMD=/run/new/pkg_add' if value=='NATIVE_PKG_ADD_CMD=/run/old/pkg_add' else value for value in cmd]
 subprocess.run(retry,check=True,capture_output=True,text=True)
 assert same.stat().st_mtime_ns==before.st_mtime_ns and same.read_text()=='same\n'
 assert changed.read_text()=='new\n' and changed.stat().st_mtime_ns!=before.st_mtime_ns
 assert obj.stat().st_ino==obj_before.st_ino and obj.stat().st_mtime_ns==obj_before.st_mtime_ns
 assert not (work/'.emberbsd-configure-preserve.json').exists()
 cookie.unlink(); (work/'change-flags').write_text('yes')
 os.utime(same,ns=(1000000000000000000,1000000000000000000)); old_mtime=same.stat().st_mtime_ns
 result=subprocess.run(cmd,check=True,capture_output=True,text=True)
 assert 'Makefile changed' in result.stdout and same.stat().st_mtime_ns != old_mtime
 report='Configuration files:\n generated/same.h\nConfiguration headers:\n config.h\nConfiguration commands:\n depfiles\n'
 assert m.inventory(report)==['generated/same.h','config.h']
 for bad in ('../escape.h','x.o','x.so.1','/outside','a/../../escape'):
  try:m.inventory(report.replace('generated/same.h',bad))
  except ValueError:pass
  else:raise AssertionError('unsafe output accepted: '+bad)
print('PASS: unchanged configure inputs retain mtime, changed outputs and objects retain their own state; failed configure retries')
