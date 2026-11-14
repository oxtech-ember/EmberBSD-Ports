#!/usr/bin/env python3
"""Owned, isolated Browser UI and persistence diagnostic; run in a GUI session."""
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time

p=argparse.ArgumentParser()
p.add_argument('--browser',required=True,help='absolute installed Browser executable')
p.add_argument('--electron',required=True,help='absolute matching Electron executable')
p.add_argument('--electron-version',required=True)
p.add_argument('--output-parent',required=True,help='existing directory for isolated diagnostic results')
a=p.parse_args()
if hasattr(os,'geteuid') and os.geteuid()==0: p.error('run as the desktop user, not root')
for name in ('browser','electron'):
    value=Path(getattr(a,name))
    if not value.is_absolute() or not value.is_file() or not os.access(value,os.X_OK): p.error(name+' must be an executable absolute path')
if not re.fullmatch(r'\d+\.\d+\.\d+',a.electron_version): p.error('invalid Electron version')
if not os.environ.get('DISPLAY'): p.error('an existing GUI display is required')
parent=Path(a.output_parent)
if not parent.is_absolute() or not parent.is_dir(): p.error('output parent must be an absolute directory')
root=Path(tempfile.mkdtemp(prefix='browser-permissions-',dir=parent))
for name in ('home','config','cache','data','results','fixture'):(root/name).mkdir(mode=0o700)
fixture=root/'fixture'
for name in ('fixture.html','private-policy.html'):
    (fixture/name).write_text("""<!doctype html><title>Browser permission fixture</title><button id=permission>Request location</button><script>window.permissionResult='idle';window.permissionRequests=0;document.querySelector('#permission').onclick=()=>{window.permissionRequests++;window.permissionResult='pending';navigator.geolocation.getCurrentPosition(()=>window.permissionResult='unexpected-grant',e=>window.permissionResult=e.code===1?'denied':'position-error-'+e.code,{timeout:8000,maximumAge:0});};</script>""")
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(fixture)))
threading.Thread(target=server.serve_forever,daemon=True).start()
target=f'http://127.0.0.1:{server.server_port}/fixture.html'
env=dict(os.environ,HOME=str(root/'home'),XDG_CONFIG_HOME=str(root/'config'),XDG_CACHE_HOME=str(root/'cache'),XDG_DATA_HOME=str(root/'data'))
env.pop('ELECTRON_RUN_AS_NODE',None)
driver=Path(__file__).resolve().with_name('browser-permissions.mjs')
owned=[]; result={'directory':str(root),'scope':'isolated Browser geolocation permission'}
def stop(process):
    for sig,seconds in ((signal.SIGTERM,5),(signal.SIGKILL,5)):
        try: os.killpg(process.pid,sig)
        except ProcessLookupError: return
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            process.poll()
            try: os.killpg(process.pid,0)
            except ProcessLookupError: return
            time.sleep(.1)
    raise RuntimeError('owned process group did not exit')
def start(phase):
    args=[a.browser,'--remote-debugging-port=0','--remote-debugging-address=127.0.0.1']
    if phase=='initial': args.append(target)
    logpath=root/(phase+'-app.log')
    with logpath.open('xb') as log:
        proc=subprocess.Popen(args,env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    owned.append(proc)
    if os.getpgid(proc.pid)!=proc.pid: raise RuntimeError('unexpected process group')
    for _ in range(300):
        if proc.poll() is not None: raise RuntimeError('Browser exited before CDP ready')
        data=logpath.read_bytes()
        if len(data)>1048576: raise RuntimeError('startup log too large')
        m=re.search(rb'DevTools listening on ws://127\.0\.0\.1:(\d+)/devtools/browser/',data)
        if m:return proc,'http://127.0.0.1:'+m.group(1).decode()
        time.sleep(.2)
    raise RuntimeError('CDP startup timeout')
try:
    for phase in ('initial','restart'):
        app,endpoint=start(phase)
        proc=subprocess.run([a.electron,str(driver),endpoint,target,str(root/'results'),phase,a.electron_version],env=dict(env,ELECTRON_RUN_AS_NODE='1'),cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
        (root/(phase+'-driver.log')).write_text(proc.stdout)
        proc.check_returncode()
        report=json.loads((root/'results'/(phase+'-flows.json')).read_text())
        if report.get('passed') is not True or report.get('phase')!=phase: raise RuntimeError('driver did not confirm phase')
        if app.wait(timeout=30)!=0: raise RuntimeError('normal Browser quit failed')
        for _ in range(50):
            try:os.killpg(app.pid,0)
            except ProcessLookupError:break
            time.sleep(.1)
        else:raise RuntimeError('owned group remained after normal quit')
        owned.remove(app);result[phase]={'normalExit':0,'ownedGroupGone':True}
    result['passed']=True
except Exception as e:
    result['passed']=False;result['error']=str(e)
finally:
    for process in owned:
        try:stop(process)
        except Exception as e:result['passed']=False;result['cleanupError']=str(e)
    server.shutdown();server.server_close()
    (root/'run.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
raise SystemExit(0 if result['passed'] else 1)
