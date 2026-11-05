#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify cross-bulk configure invocation and shared-pair guard."""
import argparse
from pathlib import Path
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
 (work/'.emberbsd-configure-preserve.json').write_text('{}')
 result=subprocess.run([str(a.shell),str(script)],capture_output=True,text=True)
 assert result.returncode and 'configure recovery is pending' in result.stderr
print('PASS: native arguments retained, active target shared pairs skipped and pending recovery protected')
