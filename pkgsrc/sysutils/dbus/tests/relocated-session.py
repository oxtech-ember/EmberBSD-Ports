import os,shutil,tempfile,subprocess,re,signal,time,socket,threading
from pathlib import Path
import sys
if len(sys.argv) != 4: raise SystemExit('usage: relocated-session.py STAGED_PREFIX ORIGINAL_PREFIX SDK_SOURCE')
sys.path.insert(0, str(Path(sys.argv[3]) / 'src'))
from emberbsd_sdk.bootstrap_bundle import relocate_text
P=Path(sys.argv[2]).resolve(); staged=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='dbus-relocated-',dir='/tmp') as d:
 root=Path(d);shutil.copytree(staged,root,dirs_exist_ok=True,symlinks=True)
 for f in (root/'share/dbus-1').glob('*.conf'):
  b=f.read_bytes();f.write_bytes(relocate_text(b,str(P).encode(),str(root).encode()))
 (root/'var/lib/dbus').mkdir(parents=True,exist_ok=True); (root/'var/lib/dbus/machine-id').write_text('0123456789abcdef0123456789abcdef\n')
 (root/'xdgdata').mkdir();(root/'runtime').mkdir(mode=0o700)
 env=os.environ.copy()
 for k in ('DBUS_SESSION_BUS_ADDRESS','DBUS_SYSTEM_BUS_ADDRESS','DBUS_STARTER_ADDRESS','DBUS_STARTER_BUS_TYPE','DISPLAY','DYLD_LIBRARY_PATH','LD_LIBRARY_PATH'):env.pop(k,None)
 env.update({'PATH':str(root/'bin')+':'+str(P/'bin')+':'+str(P/'gnu'), 'DYLD_LIBRARY_PATH':str(root/'lib'),'XDG_DATA_HOME':str(root/'xdgdata'),'XDG_DATA_DIRS':str(root/'xdgdata'),'XDG_RUNTIME_DIR':str(root/'runtime')})
 wrapper=root/'service.sh';pidfile=root/'service.pid';name='org.emberbsd.RelocationProbe';wrapper.write_text('#!/bin/sh\nprintf "%s" "$$" > "'+str(pidfile)+'"\nexec "'+str(root/'bin/dbus-test-tool')+'" echo --name='+name+'\n');wrapper.chmod(0o755)
 sd=root/'share/dbus-1/services';sd.mkdir(parents=True,exist_ok=True);(sd/(name+'.service')).write_text('[D-BUS Service]\nName='+name+'\nExec='+str(wrapper)+'\n')
 launch=subprocess.run([str(root/'bin/dbus-launch'),'--sh-syntax'],env=env,text=True,capture_output=True,timeout=15)
 if launch.returncode:raise SystemExit('launch FAIL '+launch.stderr[-1500:])
 ma=re.search(r"DBUS_SESSION_BUS_ADDRESS='([^']+)'",launch.stdout);mp=re.search(r'DBUS_SESSION_BUS_PID=(\d+)',launch.stdout)
 if not (ma and mp):raise SystemExit('launch output FAIL '+launch.stdout)
 daemon=int(mp.group(1));env['DBUS_SESSION_BUS_ADDRESS']=ma.group(1)
 try:
  proc=subprocess.run([str(root/'bin/dbus-send'),'--session','--print-reply','--dest='+name,'/org/emberbsd/Probe','org.emberbsd.Probe.Ping'],env=env,text=True,capture_output=True,timeout=15)
  if proc.returncode or not pidfile.exists():raise SystemExit('activation FAIL '+str(proc.returncode)+' '+proc.stderr[-1200:])
  print('private session + relocated daemon/config/service activation PASS')
  proc=subprocess.run([str(root/'bin/dbus-uuidgen'),'--get'],env=env,text=True,capture_output=True,timeout=10)
  if proc.returncode or '0123456789abcdef0123456789abcdef' not in proc.stdout:raise SystemExit('machine-id FAIL '+proc.stdout+' '+proc.stderr)
  print('relocated machine-id PASS')
  default_socket=root/'var/run/dbus/system_bus_socket';default_socket.parent.mkdir(parents=True,exist_ok=True)
  external_socket=root/'runtime/explicit.sock'
  def probe_system(which):
   sockets=[]; hits=[]
   try:
    for path in (default_socket,external_socket):
     listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);listener.bind(str(path));listener.listen(1);listener.settimeout(4);sockets.append(listener)
    def accept(listener,label):
     try:
      conn,_=listener.accept();hits.append(label);conn.close()
     except (OSError,TimeoutError):pass
    threads=[threading.Thread(target=accept,args=(listener,label),daemon=True) for listener,label in zip(sockets,('default','explicit'))]
    for th in threads:th.start()
    e=env.copy();e.pop('DBUS_SYSTEM_BUS_ADDRESS',None)
    if which=='explicit':e['DBUS_SYSTEM_BUS_ADDRESS']='unix:path='+str(external_socket)
    subprocess.run([str(root/'bin/dbus-send'),'--system','--print-reply','--dest=org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus.ListNames'],env=e,capture_output=True,timeout=6)
    for th in threads:th.join(timeout=5)
    if hits!=[which]:raise SystemExit('system address '+which+' FAIL '+repr(hits))
    print('system '+which+' private endpoint PASS')
   finally:
    for listener in sockets:listener.close()
    for path in (default_socket,external_socket):
     if path.exists():path.unlink()
  probe_system('default');probe_system('explicit')
 finally:
  if pidfile.exists():
   try:os.kill(int(pidfile.read_text()),signal.SIGTERM)
   except ProcessLookupError:pass
  try:os.kill(daemon,signal.SIGTERM)
  except ProcessLookupError:pass
