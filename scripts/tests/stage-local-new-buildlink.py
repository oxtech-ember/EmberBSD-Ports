#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Refresh newly added buildlink providers from the locked configure path."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--python', required=True)
a = p.parse_args()
source = Path(__file__).resolve().parents[1] / 'stage-local-configure-preserve.py'
spec = importlib.util.spec_from_file_location('configure_preserve', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix='stage-new-buildlink-') as temp:
    root = Path(temp).resolve()
    work = root / 'work'
    live = work / '.buildlink'
    recipe = root / 'recipe'
    prefix = root / 'prefix'
    (live / 'include').mkdir(parents=True)
    recipe.mkdir()
    (prefix / 'include/KHR').mkdir(parents=True)
    (prefix / 'include/KHR/khrplatform.h').write_text('egl header\n')
    (prefix / 'include/old.h').write_text('old provider\n')
    obj = work / 'kept.o'
    obj.parent.mkdir(exist_ok=True)
    obj.write_text('object\n')
    demo_cookie = live / '.buildlink_demo_done'
    old = live / 'include/old.h'
    old.symlink_to(prefix / 'include/old.h')
    demo_cookie.write_text(f'{old} -> {prefix}/include/old.h\n')
    demo_before = demo_cookie.stat()
    object_before = obj.stat()
    pkginfo = root / 'pkginfo.py'
    pkginfo.write_text("print('File: include/KHR/khrplatform.h')\n")
    fake = root / 'bmake'
    fake.write_text('''#!''' + a.python + '''
import os,pathlib,sys
a=sys.argv[1:]; r=pathlib.Path(''' + repr(str(root)) + '''); work=r/'work'; live=work/'.buildlink'; prefix=r/'prefix'
values={'_BLNK_PACKAGES':'demo egl-headers','_BLNK_COOKIE.demo':str(live/'.buildlink_demo_done'),
 '_BLNK_COOKIE.egl-headers':str(live/'.buildlink_egl-headers_done'),
 '_BLNK_COOKIE.badla':str(live/'.buildlink_badla_done'),'WRKDIR':str(work),
 'BUILDLINK_DIR':str(live),'BUILDLINK_X11_DIR':str(live),'USE_BUILTIN.egl-headers':'no',
 'BUILDLINK_PREFIX.egl-headers':str(prefix),'TOOLS_CROSS_DESTDIR':'',
 'BUILDLINK_PKGNAME.egl-headers':'egl-headers-1','_BLNK_PKG_INFO.egl-headers':sys.executable+' '+str(r/'pkginfo.py'),
 '_BLNK_FILES_CMD.egl-headers':'true','GREP':'/usr/bin/grep','USE_CROSS_COMPILE':'no'}
if (r/'include-badla').exists(): values['_BLNK_PACKAGES']+=' badla'
if '_PKGSRC_BARRIER=yes' not in a:
 for provider in ('demo','egl-headers','badla'): values['_BLNK_COOKIE.'+provider]=''
for provider in ('demo','badla'):
 values.update({'USE_BUILTIN.'+provider:'no','BUILDLINK_PREFIX.'+provider:str(prefix),
  'BUILDLINK_PKGNAME.'+provider:provider+'-1','_BLNK_PKG_INFO.'+provider:sys.executable+' '+str(r/'pkginfo.py'),
  '_BLNK_FILES_CMD.'+provider:'true'})
if '-V' in a:
 for i,x in enumerate(a):
  if x=='-V': print(values.get(a[i+1][2:-1],''))
 sys.exit(0)
target=next((x for x in a if x.startswith('buildlink-')),None)
if target:
 provider=target[len('buildlink-'):]; d=pathlib.Path(next((x.split('=',1)[1] for x in a if x.startswith('BUILDLINK_DIR=')),str(live)))
 dest=d/('include/KHR/khrplatform.h' if provider=='egl-headers' else 'include/bad.h')
 dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.is_symlink(): dest.unlink()
 dest.symlink_to(prefix/'include/KHR/khrplatform.h')
 if provider=='badla': (d/'lib').mkdir(); (d/'lib/bad.la').write_text('new .la\\n')
 if provider=='egl-headers' and (r/'fail-refresh').exists() and any(x.startswith('_BLNK_COOKIE.egl-headers=') for x in a): sys.exit(1)
 cookie=pathlib.Path(next((x.split('=',1)[1] for x in a if x.startswith('_BLNK_COOKIE.'+provider+'=')),str(d/('.buildlink_'+provider+'_done'))))
 cookie.parent.mkdir(parents=True,exist_ok=True); cookie.write_text(str(dest)+' -> '+str(prefix/'include/KHR/khrplatform.h')+'\\n')
''')
    fake.chmod(0o755)
    args = SimpleNamespace(bmake=fake, recipe=recipe, make_arg=[], bmake_args=[])
    command = [str(fake), '-C', str(recipe)]
    lazy = subprocess.run(command + ['-V', '${_BLNK_COOKIE.egl-headers}'], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.strip()
    barrier = subprocess.run(command + ['_PKGSRC_BARRIER=yes', '-V', '${_BLNK_COOKIE.egl-headers}'],
                             check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    assert not lazy and barrier == str(live / '.buildlink_egl-headers_done')
    header_link = live / 'include/KHR/khrplatform.h'
    egl_cookie = live / '.buildlink_egl-headers_done'
    (root / 'fail-refresh').touch()
    try:
        module.refresh_new_buildlinks(args, command, work)
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError('interrupted new-provider refresh unexpectedly succeeded')
    assert header_link.is_symlink() and not egl_cookie.exists()
    (root / 'fail-refresh').unlink()
    module.refresh_new_buildlinks(args, command, work)
    assert header_link.is_symlink() and os.readlink(header_link) == str(prefix / 'include/KHR/khrplatform.h')
    assert egl_cookie.is_file() and not (live / '.buildlink_badla_done').exists()
    cookie_after = egl_cookie.stat()
    module.refresh_new_buildlinks(args, command, work)
    assert (egl_cookie.stat().st_ino, egl_cookie.stat().st_mtime_ns) == (cookie_after.st_ino, cookie_after.st_mtime_ns)
    assert (demo_cookie.stat().st_ino, demo_cookie.stat().st_mtime_ns) == (demo_before.st_ino, demo_before.st_mtime_ns)
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == (object_before.st_ino, object_before.st_mtime_ns)
    (root / 'include-badla').touch()
    try:
        module.refresh_new_buildlinks(args, command, work)
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError('unsupported .la output was accepted')
    assert not (live / 'include/bad.h').exists()
print('PASS: new provider installed, existing provider cookie and object preserved, repeat idempotent, .la refusal safe')
