#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise pair lock planning, guarded cleanup and a held consumer lock."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--python',required=True,type=Path)
p.add_argument('--shell',required=True,type=Path)
p.add_argument('--sdk-source',required=True,type=Path)
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
source=(root/'cross-bulk.sh').read_text()
def function(name, close='}'):
 start=source.index(name+'()\n');end=source.index('\n'+close,start)+2
 return source[start:end]
functions='\n'.join((function('shared_pair_for_path'),function('shared_pair_config'),
                     function('package_stage_nodes',')'),function('stage_verify_locked'),
                     function('shared_pair_reset_stage')))
sys.path.insert(0,str(a.sdk_source/'src'))
from emberbsd_sdk import paths, process
with tempfile.TemporaryDirectory(prefix='paired-stage-lock-') as tmp:
 base=Path(tmp).resolve();state=base/'state';state.mkdir();run=base/'run';run.mkdir();obj=base/'obj';obj.mkdir()
 producer='x11/qt6-qtbase';consumer='x11/qt6-qtbase-devel'
 (state/'order').write_text(producer+'\n'+consumer+'\n')
 script=base/'fixture.sh';script.write_text(functions+'''
state=$1 run=$2 mode=$3 role=$4 path=$5 requested=$6
CROSS_BULK_SHARED_BUILD=$7
package_stage_nodes
''')
 def plan(mode,role,path,requested=None,shared='yes'):
  r=subprocess.run([str(a.shell),str(script),str(state),str(run),mode,role,path,requested or path,shared],check=True,capture_output=True,text=True)
  return r.stdout.splitlines()
 assert plan('package','target',producer)==[producer,consumer]
 assert plan('package','target',consumer)==[consumer,producer]
 assert plan('package-install','target',producer)==[producer,consumer]
 for mode in ('patch-refresh','buildlink-refresh'):
  assert plan(mode,'target',producer)==[producer]
 assert plan('package','native',producer,producer+'@native')==[producer+'@native']
 assert plan('package','target',producer,shared='no')==[producer]
 (state/'order').write_text(producer+'\n')
 assert plan('package','target',producer)==[producer]
 (state/'order').write_text(producer+'\n'+consumer+'\n')
 # Guard the actual shared cleanup before its bmake command can run.
 (run/'shared-qtbase').mkdir();(run/'shared-qtbase/enabled').write_text('yes\n')
 marker=base/'cleanup-called';manifest=base/'manifest';work=obj/'consumer';work.mkdir()
 guard=base/'guard.sh';guard.write_text(functions+'''
run=$1; state=$2; PKGSRCDIR=$3; stage_local=yes; stage_supervised=yes
CROSS_BULK_STAGE_MANIFEST=$4; CLEANUP_MARKER=$5; WORK=$6
pkg_vars() { printf '%s\\n' "$WORK"; }
bmk() { : > "$CLEANUP_MARKER"; }
shared_pair_reset_stage x11/qt6-qtbase-devel
''')
 manifest.write_text(str(obj/'other')+'\n')
 args=[str(a.shell),str(guard),str(run),str(state),str(base),str(manifest),str(marker),str(work)]
 denied=subprocess.run(args,capture_output=True,text=True)
 assert denied.returncode and not marker.exists() and 'not locked' in denied.stderr, denied.stderr
 manifest.write_text(str(work)+'\n')
 subprocess.run(args,check=True,capture_output=True,text=True);assert marker.exists()
 # A real SDK lock held for the consumer must prevent the pair worker from
 # entering, even though the producer is free. After release both are held.
 pwork=obj/'producer';pwork.mkdir();cwork=work
 specs=[{'root':str(obj),'work':str(pwork)},{'root':str(obj),'work':str(cwork)}]
 specfile=base/'locks.json';specfile.write_text(json.dumps(specs));started=base/'started'
 supervisor=[str(a.python),'-B',str(root/'stage-context-supervisor.py'),'--sdk-source',str(a.sdk_source),'--locks',str(specfile),'--',str(a.shell),'-c',': > "$1"','worker',str(started)]
 with process.ContextLocks([paths.canonical_new(str(cwork))],paths.canonical_existing(str(obj))):
  blocked=subprocess.run(supervisor,capture_output=True,text=True,timeout=15)
  assert blocked.returncode and 'object context is busy' in blocked.stderr and not started.exists(),blocked.stderr
 subprocess.run(supervisor,check=True,capture_output=True,text=True,timeout=15)
 assert started.exists()
print('PASS: both pair directions planned; single-stage modes isolated; unlocked cleanup refused; held consumer blocks pair worker')
