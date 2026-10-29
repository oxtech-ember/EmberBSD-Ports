#!/usr/bin/env python3
"""Check pkg_add/pkg_delete script environment using isolated real packages."""
import argparse, os, pathlib, platform, subprocess, tempfile
p=argparse.ArgumentParser()
for arg in ('pkg-add','pkg-delete','pkg-create'):
 p.add_argument('--'+arg, type=pathlib.Path, required=True)
a=p.parse_args()
assert all(path.is_absolute() and path.is_file() for path in (a.pkg_add, a.pkg_delete, a.pkg_create))
assert str(a.pkg_delete).encode() in a.pkg_add.read_bytes(), 'pkg_add must use the selected pkg_delete for replacement'
def run(args, env):
 r=subprocess.run([str(x) for x in args],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if r.returncode: raise RuntimeError(r.stdout)
 return r.stdout
with tempfile.TemporaryDirectory(prefix='pkg-script-env-') as d:
 d=pathlib.Path(d); prefix=d/'active'; stage=d/'stage'; prefix.mkdir(); stage.mkdir(); db=prefix/'pkgdb'; db.mkdir(); (prefix/'sentinel').write_text('unchanged')
 env=dict(os.environ); env.pop('PKG_DESTDIR',None); env.pop('PKG_REFCOUNT_DBDIR',None); env.pop('PKG_PATH',None)
 script=d/'script'; script.write_text('''#!/bin/sh
set -eu
: "${TEST_LOG:?}" "${PKG_METADATA_DIR:?}" "${PKG_REFCOUNT_DBDIR:?}" "${PKG_PREFIX:?}"
printf '%s|%s|%s|%s|%s\\n' "$1" "$2" "${PKG_DESTDIR-}" "$PKG_METADATA_DIR" "$PKG_REFCOUNT_DBDIR" >> "$TEST_LOG"
if [ "$1" = parent-1 ] && [ "$2" = PRE-INSTALL ]; then
  "$TEST_ADD" -P "$PKG_DESTDIR" -K "$TEST_DB" "$TEST_CHILD"
fi
'''); script.chmod(0o755)
 buildinfo=d/'buildinfo'; arch={'arm64':'aarch64'}.get(platform.machine(),platform.machine()); buildinfo.write_text(f'OPSYS={platform.system()}\nOS_VERSION={platform.release()}\nMACHINE_ARCH={arch}\n')
 plist=d/'plist'
 def package(name):
  filename=name.split('-')[0]+'.txt'; (prefix/filename).write_text('fixture'); plist.write_text('@cwd '+str(prefix)+'\n'+filename+'\n')
  archive=d/(name+'.tgz'); run([a.pkg_create,'-c','-fixture','-d','-fixture','-f',plist,'-B',buildinfo,'-i',script,'-k',script,'-p',prefix,archive],env); return archive
 child=package('child-1'); parent=package('parent-1'); env.update(TEST_LOG=str(d/'log'),TEST_ADD=str(a.pkg_add),TEST_CHILD=str(child),TEST_DB=str(db))
 run([a.pkg_add,'-P',stage,'-K',db,parent],env)
 log=(d/'log').read_text().splitlines(); assert len(log)>=4,log
 expected=str(stage)+str(db)+'.refcount'; assert all(os.path.normpath(x.split('|')[4]) == expected for x in log),log
 assert all(x.split('|')[2]==str(stage) and os.path.normpath(x.split('|')[3]).startswith(str(stage)+str(db)+'/') for x in log),log
 assert (prefix/'sentinel').read_text()=='unchanged'
 before=(d/'log').read_text()
 upgrade=package('parent-2')
 run([a.pkg_add,'-n','-U','-P',stage,'-K',db,upgrade],env)
 assert (d/'log').read_text()==before
 run([a.pkg_add,'-U','-P',stage,'-K',db,upgrade],env)
 upgrade_log=(d/'log').read_text().splitlines()
 assert any(x.startswith('parent-1|DEINSTALL|') for x in upgrade_log),upgrade_log
 assert any(x.startswith('parent-2|POST-INSTALL|') for x in upgrade_log),upgrade_log
 run([a.pkg_delete,'-P',stage,'-K',db,'parent-2','child-1'],env)
 log=(d/'log').read_text().splitlines(); assert any(x.startswith('child-1|DEINSTALL|') for x in log),log
 assert any(x.startswith('parent-2|DEINSTALL|') for x in log),log
 assert all(os.path.normpath(x.split('|')[4]) == expected and x.split('|')[2] == str(stage) for x in log),log
 # On a first invocation a logical refcount path inside the stage root is
 # still prefixed. It is not an inherited physical script context.
 custom=package('custom-1'); custom_env=dict(env,PKG_REFCOUNT_DBDIR=str(stage/'logical-refcounts'))
 custom_env.pop('PKG_DESTDIR',None)
 run([a.pkg_add,'-P',stage,'-K',db,custom],custom_env)
 custom_log=(d/'log').read_text().splitlines()[-2:]
 assert all(os.path.normpath(x.split('|')[4])==str(stage)+str(stage/'logical-refcounts') for x in custom_log),custom_log
 # Inherited DESTDIR alone does not turn the default logical db into an
 # inherited physical refcount path.
 absent=package('absent-1'); nested_db=stage/'logical-db'; inherited_env=dict(env,PKG_DESTDIR=str(stage)); inherited_env.pop('PKG_REFCOUNT_DBDIR',None)
 run([a.pkg_add,'-P',stage,'-K',nested_db,absent],inherited_env)
 absent_log=(d/'log').read_text().splitlines()[-2:]
 assert all(os.path.normpath(x.split('|')[4])==str(stage)+str(nested_db)+'.refcount' for x in absent_log),absent_log
 # No -P keeps the caller's deliberately inherited PKG_DESTDIR.
 solo=package('solo-1'); env['PKG_DESTDIR']='inherited-value'; run([a.pkg_add,'-K',db,solo],env)
 no_stage=(d/'log').read_text().splitlines()[-2:]
 assert all(x.split('|')[2]=='inherited-value' and x.split('|')[4]==str(db)+'.refcount' for x in no_stage),no_stage
 run([a.pkg_delete,'-K',db,'solo-1'],env)
 assert (prefix/'sentinel').read_text()=='unchanged'
 print('PASS staged and ordinary script environment, nested add, replacement and deletion')
