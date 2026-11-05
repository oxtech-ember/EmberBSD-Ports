#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""A dead outer owner must not release a still-writing stage session."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--python',required=True,type=Path);p.add_argument('--shell',required=True,type=Path);p.add_argument('--sdk-source',required=True,type=Path)
a=p.parse_args();helper=Path(__file__).resolve().parents[1]/'stage-context-supervisor.py'
with tempfile.TemporaryDirectory(prefix='pkgsrc-supervisor-test-') as tmp:
 root=Path(tmp); obj=root/'obj';obj.mkdir();work=obj/'category/pkg/work';state1=root/'state1';state2=root/'state2';state1.mkdir();state2.mkdir()
 spec=[dict(root=str(obj),work=str(work))]
 (state1/'locks.json').write_text(json.dumps(spec))
 # A different WRKOBJDIR that still contains the same stage must not select
 # a different lock file.
 alternate=[dict(root=str(obj/'category'),work=str(work))]
 (state2/'locks.json').write_text(json.dumps(alternate))
 ready=root/'ready';done=root/'done';worker=root/'worker.py'
 worker.write_text('import pathlib,sys,time\np=pathlib.Path(sys.argv[1]);p.write_text("ready")\ntime.sleep(2)\npathlib.Path(sys.argv[2]).write_text("done")\n')
 command=[str(a.python),'-B',str(helper),'--sdk-source',str(a.sdk_source),'--locks',str(state1/'locks.json'),'--',str(a.python),'-B',str(worker),str(ready),str(done)]
 parent=subprocess.Popen([str(a.shell),'-c','"$@" & wait','parent',*command],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 end=time.monotonic()+15
 while not ready.exists() and parent.poll() is None and time.monotonic()<end:time.sleep(.02)
 assert ready.exists(), 'first worker did not acquire the stage'
 os.kill(parent.pid,signal.SIGKILL);parent.wait()
 second=[str(a.python),'-B',str(helper),'--sdk-source',str(a.sdk_source),'--locks',str(state2/'locks.json'),'--',str(a.python),'-B','-c','pass']
 busy=subprocess.run(second,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=10)
 assert busy.returncode != 0 and 'object context is busy' in busy.stderr, busy.stderr
 end=time.monotonic()+20
 while not done.exists() and time.monotonic()<end:time.sleep(.02)
 assert done.exists(), 'orphaned writer was terminated or lost its stage'
 end=time.monotonic()+20
 while True:
  retry=subprocess.run(second,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=10)
  if retry.returncode==0:break
  assert 'object context is busy' in retry.stderr and time.monotonic()<end, retry.stderr
  time.sleep(.05)
 # Kill the supervised stage shell itself while its child still writes.
 ready.unlink();done.unlink();leader=root/'leader'
 shell_script='printf "%s\\n" "$$" > "$1"; "$2" -B "$3" "$4" "$5" & wait'
 supervised=[str(a.python),'-B',str(helper),'--sdk-source',str(a.sdk_source),'--locks',str(state1/'locks.json'),'--',str(a.shell),'-c',shell_script,'stage',str(leader),str(a.python),str(worker),str(ready),str(done)]
 supervisor=subprocess.Popen(supervised,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
 end=time.monotonic()+15
 while not ready.exists() and supervisor.poll() is None and time.monotonic()<end:time.sleep(.02)
 assert ready.exists(), supervisor.stderr.read() if supervisor.poll() is not None else 'stage did not start'
 os.kill(int(leader.read_text().strip()),signal.SIGKILL)
 busy=subprocess.run(second,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=10)
 assert busy.returncode != 0 and 'object context is busy' in busy.stderr, busy.stderr
 end=time.monotonic()+20
 while not done.exists() and time.monotonic()<end:time.sleep(.02)
 assert done.exists(), 'stage child writer was killed when its shell died'
 assert supervisor.wait(timeout=20)==137, supervisor.stderr.read()
 assert subprocess.run(second,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=10).returncode==0
 # Injected SDK inspection failure cannot release locks while unresolved.
 sys.path.insert(0,str(a.sdk_source/'src'))
 from emberbsd_sdk import paths, process
 from emberbsd_sdk.errors import ProcessOwnershipError
 specmod=importlib.util.spec_from_file_location('stage_supervisor',helper)
 mod=importlib.util.module_from_spec(specmod);specmod.loader.exec_module(mod)
 failed=root/'inspection-failed';resume=root/'inspection-resume'
 pid=os.fork()
 if pid==0:
  class FailingGroup:
   def stop(self):
    if not resume.exists():
     failed.write_text('pending')
     raise ProcessOwnershipError(123,'injected inspection failure')
  with process.ContextLocks([paths.canonical_new(str(work))], paths.canonical_existing(str(work.parent))):
   mod.drain_or_hold(FailingGroup(),ProcessOwnershipError,delay=.02)
  os._exit(0)
 end=time.monotonic()+10
 while not failed.exists() and time.monotonic()<end:time.sleep(.02)
 assert failed.exists()
 busy=subprocess.run(second,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=10)
 assert busy.returncode != 0 and 'object context is busy' in busy.stderr, busy.stderr
 resume.write_text('resume');_,status=os.waitpid(pid,0);assert os.waitstatus_to_exitcode(status)==0
 assert subprocess.run(second,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=10).returncode==0
print('owner crash retains stage lock until child session drains')
