#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify cross-bulk configure invocation and shared-pair guard."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--shell',type=Path,required=True);a=p.parse_args()
source=(Path(__file__).resolve().parents[1]/'cross-bulk.sh').read_text()
def function(name):
 start=source.index(name+'()\n{');end=source.index('\n}',start)+2;return source[start:end]
with tempfile.TemporaryDirectory(prefix='stage-configure-bulk-') as tmp:
 root=Path(tmp).resolve();run=root/'run';(run/'shared-icu').mkdir(parents=True)
 work=root/'work';work.mkdir();printer=root/'print';printer.write_text('#!'+str(a.shell)+'\nprintf "<%s>\\n" "$@"\n');printer.chmod(0o755)
 script=root/'fixture.sh';script.write_text(function('stage_configure_preserve')+'\n'+function('stage_configure_preserve_target')+'''
shared_pair_for_path() { case "$1" in textproc/icu) shared_pair=icu;; *) shared_pair=;; esac; }
sdk_source=/sdk BMAKE=/selected/bmake PKGSRCDIR=/pkgsrc native=verified make_jobs=2
run="'''+str(run)+'''" cachearg="/cache with space" link_args= host_python="'''+str(printer)+'''"
stage_configure_preserve textproc/libxml2 "'''+str(work)+'''" USE_CROSS_COMPILE=no "NATIVE_SETTING=with space"
install=package-install
stage_configure_preserve_target textproc/libxml2 "'''+str(work)+'''" TARGET_SETTING=yes
stage_configure_preserve_target textproc/icu "'''+str(work)+'''" SHOULD_NOT_RUN=yes
''')
 (run/'shared-icu/enabled').write_text('yes\n')
 result=subprocess.run([str(a.shell),str(script)],check=True,capture_output=True,text=True)
 assert '<USE_CROSS_COMPILE=no>' in result.stdout and '<NATIVE_SETTING=with space>' in result.stdout
 assert '<PBULK_CACHE_DIRECTORY=/cache with space>' in result.stdout and 'SHOULD_NOT_RUN' not in result.stdout
 assert '<TARGET_SETTING=yes>' in result.stdout and '<PKGSRC_KEEP_BIN_PKGS=yes>' in result.stdout
 assert '_EMBER_STAGE_LOCAL_' not in result.stdout
 stage_result=subprocess.run([str(a.shell),str(script)],check=True,capture_output=True,text=True,
                             env=dict(os.environ,stage_local='yes'))
 (work/'.emberbsd-configure-preserve.json').write_text('{}')
 result=subprocess.run([str(a.shell),str(script)],capture_output=True,text=True)
 assert result.returncode and 'configure recovery is pending' in result.stderr
 # Exercise the ordinary worker entry points, not just their helper. Before
 # this regression, both workers skipped preservation unless stage_local=yes.
 (work/'.emberbsd-configure-preserve.json').unlink()
 (root/'logs').mkdir();(run/'crossfed').write_text('')
 common='\n'.join(function(n) for n in ('build_one','build_native','stage_configure_preserve_target'))
 common+='''
stage_local=no job=1 native_packages=/native-packages target_settings= build_vars_context=
state='''+shlex.quote(str(root))+''' run='''+shlex.quote(str(run))+''' work='''+shlex.quote(str(work))+'''
trace="$state/trace" PKGSRCDIR=/pkgsrc target_pkg_info=false native_pkg_info=false
pkg_vars() { printf '%s\\n' test-1.0 "$work" '' test 1.0 "$state/test.tgz" "$state"; }
stage_verify_locked() { [ "$1" = "$work" ]; }
native_current() { return 1; }
shared_pair_restore_producer() { return 0; }
shared_pair_for_path() { shared_pair=; }
prepare_wrkdir() {
    printf '%s\\n' prepare >> "$trace"
    [ "$scenario" != dependencies ] || { prepare_wrkdir_error=workdir-dependency-change; return 1; }
    clean=
}
stage_configure_preserve() {
    printf 'configure %s\\n' "$*" >> "$trace"
    [ "$scenario" != configure-failure ]
}
# Stop at the install boundary: no package, dependency or object is built here.
target_install() { printf 'install %s\\n' "$*" >> "$trace"; return 1; }
bmk() { printf 'install %s\\n' "$*" >> "$trace"; return 1; }
result() { printf 'result %s\\n' "$*" >> "$trace"; }
'''
 for role in ('target','native'):
  for scenario in ('ready','configure-failure','dependencies'):
   trace=root/'trace';trace.write_text('')
   call='build_one textproc/test' if role=='target' else 'build_native textproc/test@native test'
   script.write_text(common+'\nscenario='+scenario+'\n'+call+'\n')
   subprocess.run([str(a.shell),str(script)],check=True,capture_output=True,text=True)
   lines=trace.read_text().splitlines()
   assert lines[0]=='prepare', (role,scenario,lines)
   assert '_EMBER_STAGE_LOCAL_' not in trace.read_text()
   if scenario=='dependencies':
    assert len(lines)==2 and 'workdir-dependency-change' in lines[-1], lines
   else:
    assert lines[1].startswith('configure textproc/test '+str(work)), lines
    if role=='native':
     assert 'USE_CROSS_COMPILE=no PACKAGES=/native-packages _AUTOMATIC=yes' in lines[1], lines
    else:
     assert 'PKGSRC_KEEP_BIN_PKGS=yes' in lines[1], lines
    if scenario=='ready':
     assert lines[2].startswith('install '), lines
    else:
     assert len(lines)==3 and lines[2].startswith('result '), lines
 assert '<_EMBER_STAGE_LOCAL_PACKAGE_INSTALL=yes>' in stage_result.stdout
 assert '<_EMBER_STAGE_LOCAL_PKGPATH=textproc/libxml2>' in stage_result.stdout
 assert '<_EMBER_STAGE_LOCAL_WRKDIR='+str(work)+'>' in stage_result.stdout
print('PASS: ordinary native/target workers preserve configuration before install, keep role arguments and stop on failures; scoped flags and shared-pair guards remain')
