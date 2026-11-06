#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise provider replacement, collisions and retry using a recording factory."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--python', required=True)
a = p.parse_args()
helper = Path(__file__).resolve().parents[1] / 'stage-local-buildlink-refresh.py'
with tempfile.TemporaryDirectory(prefix='buildlink-refresh-test-') as t:
    root = Path(t); work = root / 'work'; live = work / '.buildlink'; recipe = root / 'recipe'; prefix = root / 'cross/usr/pkg'
    live.mkdir(parents=True); recipe.mkdir(); prefix.mkdir(parents=True)
    (work / 'retained.o').write_bytes(b'object')
    src = prefix / 'include'; src.mkdir(); (src / 'old.h').write_text('old'); (src / 'new.h').write_text('new'); (src / 'common.h').write_text('common')
    (live / 'include').mkdir(); (live / 'lib').mkdir()
    os.symlink(src / 'old.h', live / 'include/old.h')
    os.symlink(src / 'common.h', live / 'include/common.h')
    cookie = live / '.buildlink_demo_done'
    cookie.write_text(f'{live}/include/old.h -> {src}/old.h\n{live}/include/common.h -> {src}/common.h\n')
    (live / 'lib/demo.la').write_text(f"libdir='{live}/lib'\n")
    fake = root / 'bmake'
    fake.write_text('''#!''' + a.python + '''
import os,pathlib,sys
args=sys.argv[1:]; cfg=''' + repr(str(root)) + '''
r=pathlib.Path(cfg); live=r/'work/.buildlink'; prefix=r/'cross/usr/pkg'; vals={'WRKDIR':str(r/'work'),'BUILDLINK_DIR':str(live),'BUILDLINK_X11_DIR':str(live),'USE_BUILTIN.demo':'no','BUILDLINK_PREFIX.demo':'/usr/pkg','TOOLS_CROSS_DESTDIR':str(r/'cross'),'BUILDLINK_PKGNAME.demo':'demo-2','_BLNK_COOKIE.demo':str(live/'.buildlink_demo_done'),'_BLNK_PKG_INFO.demo':sys.executable+' '+str(r/'pkginfo.py'),'_BLNK_FILES_CMD.demo':'printf dummy','GREP':'/selected/grep'}
if '-V' in args:
 for i,x in enumerate(args):
  if x=='-V': print(vals[args[i+1][2:-1]])
 sys.exit(0)
def opt(n,default):
 return next((x.split('=',1)[1] for x in args if x.startswith(n+'=')),str(default))
d=pathlib.Path(opt('BUILDLINK_DIR',live)); cookie=pathlib.Path(opt('_BLNK_COOKIE.demo',d/'.buildlink_demo_done'))
(d/'include').mkdir(parents=True,exist_ok=True);(d/'lib').mkdir(parents=True,exist_ok=True)
common=d/'include/common.h';common.unlink(missing_ok=True)
if d==live and (r/'fail').exists(): (r/'fail').unlink();sys.exit(1)
common.symlink_to(prefix/'include/common.h')
link=d/'include/new.h';link.unlink(missing_ok=True);link.symlink_to(prefix/'include/new.h')
if d!=live:(d/'lib/demo.la').write_text("libdir='"+str(d)+"/lib'\\n")
cookie.write_text(str(common)+' -> '+str(prefix/'include/common.h')+'\\n'+str(link)+' -> '+str(prefix/'include/new.h')+'\\n')
''')
    fake.chmod(0o755)
    (root/'pkginfo.py').write_text("print('File: include/new.h')\n")
    la_stat = (live/'lib/demo.la').stat()
    obj_stat = (work/'retained.o').stat()
    cmd=[a.python,'-B',str(helper),'--bmake',str(fake),'--recipe',str(recipe),'--expected-work',str(work),'--provider','demo']
    (root/'fail').touch()
    assert subprocess.run(cmd,capture_output=True).returncode
    assert 'old.h' in cookie.read_text() and not (live/'include/common.h').exists()
    subprocess.run(cmd,check=True,capture_output=True)
    assert not (live/'include/old.h').exists() and (live/'include/new.h').is_symlink() and (live/'include/common.h').is_symlink()
    assert (work/'retained.o').read_bytes()==b'object'
    assert ((live/'lib/demo.la').stat().st_ino, (live/'lib/demo.la').stat().st_mtime_ns) == (la_stat.st_ino, la_stat.st_mtime_ns)
    assert ((work/'retained.o').stat().st_ino, (work/'retained.o').stat().st_mtime_ns) == (obj_stat.st_ino, obj_stat.st_mtime_ns)
    (live/'include/new.h').unlink(); (live/'include/new.h').write_text('foreign')
    assert subprocess.run(cmd,capture_output=True).returncode
    assert (live/'include/new.h').read_text()=='foreign'
    (live/'include/new.h').unlink(); (live/'include/common.h').unlink(); (live/'include').rmdir()
    outside = root/'outside'; outside.mkdir(); (live/'include').symlink_to(outside, target_is_directory=True)
    assert subprocess.run(cmd,capture_output=True).returncode
    assert not (outside/'new.h').exists()
print('PASS: planned factory, obsolete link, retry, retained objects, collision')
