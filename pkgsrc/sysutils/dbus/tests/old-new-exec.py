import os,shutil,subprocess,tempfile,sys
from pathlib import Path
if len(sys.argv) != 4: raise SystemExit('usage: old-new-exec.py OLD_PREFIX NEW_PREFIX INTERPOSER')
P=Path(sys.argv[1]).resolve();stage=Path(sys.argv[2]).resolve();interposer=Path(sys.argv[3]).resolve()
with tempfile.TemporaryDirectory(prefix='dbus-exec-',dir='/tmp') as t:
 root=Path(t)
 for label,base in [('old',P),('new',stage)]:
  dest=root/label; (dest/'bin').mkdir(parents=True);(dest/'lib').mkdir();shutil.copy2(base/'bin/dbus-launch',dest/'bin/dbus-launch');shutil.copy2(base/'lib/libdbus-1.3.dylib',dest/'lib/libdbus-1.3.dylib')
  trace=root/(label+'.trace');env=os.environ.copy()
  for k in ('DBUS_SESSION_BUS_ADDRESS','DBUS_SYSTEM_BUS_ADDRESS','DBUS_STARTER_ADDRESS','DISPLAY','DYLD_INSERT_LIBRARIES','LD_LIBRARY_PATH'):env.pop(k,None)
  env.update({'DYLD_LIBRARY_PATH':str(dest/'lib'),'DYLD_INSERT_LIBRARIES':str(interposer),'EMBER_DBUS_EXEC_TRACE':str(trace)})
  proc=subprocess.run([str(dest/'bin/dbus-launch'),'--sh-syntax'],env=env,text=True,capture_output=True,timeout=10)
  if not trace.exists():raise SystemExit(label+' no intercepted exec; exit='+str(proc.returncode)+' '+proc.stderr[-900:])
  actual=trace.read_text();expected=str((P if label=='old' else dest).resolve()/'bin/dbus-daemon')
  if actual!=expected:raise SystemExit(label+' wrong daemon '+actual+' expected '+expected)
  print(label, 'old-prefix detected PASS' if label=='old' else 'relocated daemon selected PASS')
