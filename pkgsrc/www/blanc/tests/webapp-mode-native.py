#!/usr/bin/env python3
"""Target WebApp acceptance. Run only in a controlled desktop session."""
import argparse,ctypes,fcntl,hashlib,json,os,re,shutil,signal,subprocess,sys,tempfile,threading,time,uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

p=argparse.ArgumentParser();p.add_argument('--browser',type=Path,required=True);p.add_argument('--helper',type=Path,required=True);p.add_argument('--sdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout',type=int,default=90);p.add_argument('--content-offset-y',type=int,required=True);p.add_argument('--diagnostic-only',action='store_true');p.add_argument('--runtime-path',required=True,help='target executable PATH including the selected package prefix');a=p.parse_args()
if os.geteuid()==0 or not 10<=a.timeout<=300 or not 0<=a.content_offset_y<=200:raise SystemExit('run as desktop user with timeout 10..300')
for q in (a.browser,a.helper,a.sdk):
 if not q.is_absolute() or q.is_symlink() or not q.is_file():raise SystemExit('explicit regular input required')
if not a.output.is_absolute() or a.output.exists() or a.output.is_symlink():raise SystemExit('new absolute output required')
if not os.environ.get('DISPLAY') or not os.environ.get('XAUTHORITY'):raise SystemExit('desktop DISPLAY and XAUTHORITY required')
a.output.mkdir(mode=0o700); evidence=a.output.resolve(); owned=[]; events=[]; event_lock=threading.Lock();token=uuid.uuid4().hex
sys.path.insert(0,str(a.sdk));from emberbsd_sdk.process import OwnedProcessGroup
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  u=urlsplit(self.path);q=parse_qs(u.query)
  if q.get('token')!=[token] or u.path not in ('/a','/b','/popup','/seen','/opener-confirm'):self.send_error(404);return
  with event_lock:events.append({'path':u.path,'tag':q.get('tag',[''])[0],'page':q.get('page',[''])[0],'cookie':self.headers.get('Cookie','')})
  if u.path in ('/seen','/opener-confirm'):
   self.send_response(204);self.send_header('Cache-Control','no-store');self.end_headers();return
  tag=q.get('tag',[''])[0]
  if u.path=='/popup':
   body=("<!doctype html><title>Popup QA</title><script>if(window.opener) window.opener.postMessage({kind:'qa-popup',nonce:'%s'},location.origin);</script>" % token).encode()
   self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
  body=("""<!doctype html><meta charset=\"utf-8\"><title>WebApp QA %s</title>
  <style>body{margin:0;font:24px sans-serif} h1{position:absolute;left:20px;top:5px;margin:0}
  a,button{position:absolute;left:20px;width:260px;height:42px;box-sizing:border-box} a{top:70px} button{top:130px}</style>
  <h1>WebApp QA %s</h1><a href=\"/b?token=%s&amp;tag=%s\">Go to page B</a>
  <button onclick=\"popup=window.open('/popup?token=%s&amp;tag=%s','qa','width=420,height=320')\">Open popup</button>
  <script>let popup=null; window.addEventListener('message',e=>{if(e.origin===location.origin && e.source===popup && e.data && e.data.kind==='qa-popup' && e.data.nonce==='%s') fetch('/opener-confirm?token=%s&tag=%s',{cache:'no-store'});});window.addEventListener('pageshow',()=>fetch('/seen?token=%s&tag=%s&page=%s',{cache:'no-store'}));</script>"""%(u.path,u.path,token,tag,token,tag,token,token,tag,token,tag,u.path)).encode()
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)))
  if q.get('set')==['1']:self.send_header('Set-Cookie','webapp_qa='+q.get('tag',[''])[0]+'; Path=/; SameSite=Lax; Max-Age=3600')
  self.end_headers();self.wfile.write(body)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_address[1]); cases={};logs=[]
root=Path(tempfile.mkdtemp(prefix='ember-webapp-qa-',dir='/var/tmp'));rootstat=root.lstat();os.chmod(root,0o700)
ordinary=root/'config/Ember Browser';(ordinary/'GPUCache').mkdir(parents=True);(ordinary/'Local State').write_text('ordinary-profile-sentinel\n');(ordinary/'GPUCache/sentinel').write_text('ordinary-cache-sentinel\n')
def ordinary_hashes():
 return {str(p.relative_to(ordinary)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ordinary/'Local State',ordinary/'GPUCache/sentinel')}
ordinary_before=ordinary_hashes()
env={k:os.environ[k] for k in ('DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR','WAYLAND_DISPLAY') if k in os.environ};env.update(HOME=str(root),XDG_CONFIG_HOME=str(root/'config'),XDG_CACHE_HOME=str(root/'cache'),XDG_DATA_HOME=str(root/'data'),PATH=a.runtime_path,LANG='C.UTF-8')
def path_url(tag,route='a',setcookie=False):return base+'/'+route+'?token='+token+'&tag='+tag+('&set=1' if setcookie else '')
def start(tag,private=False,ident=None,url=None):
 ident=ident or ('qa_'+token[:12]+'_'+tag);log=(evidence/(tag+'-'+str(len(logs))+'.log')).open('xb',buffering=0);logs.append(log)
 args=[str(a.browser),'--webapp-id='+ident,'--webapp-url='+(url or path_url(tag,setcookie=True)),'--webapp-name=QA '+tag]+(['--webapp-private'] if private else [])
 child=OwnedProcessGroup(args,cwd=str(root),env=env,stdout=log,stderr=log);child.start();owned.append(child);return child,ident
def wait_for(fn,description):
 deadline=time.monotonic()+a.timeout
 while time.monotonic()<deadline:
  result=fn()
  if result:return result
  time.sleep(.2)
 raise TimeoutError(description)
def seen(route,tag,minimum=1):
 with event_lock: rows=[e for e in events if e['path']==route and e['tag']==tag]
 return rows if len(rows)>=minimum else None
def pageshow(route,tag,minimum=1):
 with event_lock: rows=[e for e in events if e['path']=='/seen' and e['page']==route and e['tag']==tag]
 return rows if len(rows)>=minimum else None
def ui(pid,ident,action,*args,window=None):
 cmd=[str(a.helper),str(pid),'WebApp-'+ident]+(['list'] if action=='list' else [window,action,*map(str,args)])
 r=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
 if r.returncode:raise RuntimeError('X11 helper '+action+' failed: '+r.stderr[:300])
 return r.stdout
def inspect_owned_windows(pids):
 # Read-only, bounded X11 traversal; never return properties for foreign PIDs.
 x=ctypes.CDLL('libX11.so');D=ctypes.c_void_p;W=ctypes.c_ulong;U=ctypes.c_uint;L=ctypes.c_ulong;I=ctypes.c_int
 x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=D
 x.XDefaultRootWindow.argtypes=[D];x.XDefaultRootWindow.restype=W
 x.XInternAtom.argtypes=[D,ctypes.c_char_p,I];x.XInternAtom.restype=W
 x.XQueryTree.argtypes=[D,W,ctypes.POINTER(W),ctypes.POINTER(W),ctypes.POINTER(ctypes.POINTER(W)),ctypes.POINTER(U)];x.XQueryTree.restype=I
 x.XGetWindowProperty.argtypes=[D,W,W,ctypes.c_long,ctypes.c_long,I,W,ctypes.POINTER(W),ctypes.POINTER(I),ctypes.POINTER(L),ctypes.POINTER(L),ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte))];x.XGetWindowProperty.restype=I
 x.XGetGeometry.argtypes=[D,W,ctypes.POINTER(W),ctypes.POINTER(I),ctypes.POINTER(I),ctypes.POINTER(U),ctypes.POINTER(U),ctypes.POINTER(U),ctypes.POINTER(U)];x.XGetGeometry.restype=I
 x.XFree.argtypes=[ctypes.c_void_p];x.XSync.argtypes=[D,I];x.XCloseDisplay.argtypes=[D]
 handler_type=ctypes.CFUNCTYPE(I,D,ctypes.c_void_p);errors=[]
 @handler_type
 def on_error(_display,_event):errors.append(True);return 0
 x.XSetErrorHandler.argtypes=[handler_type];x.XSetErrorHandler.restype=ctypes.c_void_p;x.XSetErrorHandler(on_error)
 display=x.XOpenDisplay(None)
 if not display:raise RuntimeError('cannot open X display for owned-window inspection')
 def safe_sync():x.XSync(display,0);ok=not errors;errors.clear();return ok
 def prop(win,atom,limit):
  typ=W();fmt=I();count=L();remaining=L();data=ctypes.POINTER(ctypes.c_ubyte)()
  rc=x.XGetWindowProperty(display,win,atom,0,limit,0,0,ctypes.byref(typ),ctypes.byref(fmt),ctypes.byref(count),ctypes.byref(remaining),ctypes.byref(data))
  ok=safe_sync()
  try:
   if not ok or rc!=0 or not data:return None
   if fmt.value==32:return (typ.value,fmt.value,count.value,remaining.value,ctypes.cast(data,ctypes.POINTER(L))[0] if count.value else None)
   if fmt.value==8:return (typ.value,fmt.value,count.value,remaining.value,ctypes.string_at(data,min(count.value,limit*4)))
   return None
  finally:
   if data:x.XFree(data)
 try:
  atoms={n:x.XInternAtom(display,n.encode(),0) for n in ('_NET_WM_PID','WM_CLASS','_NET_WM_NAME','WM_NAME')}
  if not safe_sync():raise RuntimeError('X atom query failed')
  queue=[(x.XDefaultRootWindow(display),0)];visited=0;rows=[]
  while queue:
   win,depth=queue.pop();visited+=1
   if visited>10000:raise RuntimeError('X window traversal exceeded bound')
   pid=prop(win,atoms['_NET_WM_PID'],1)
   if pid and pid[0]==6 and pid[1]==32 and pid[2]==1 and pid[3]==0 and pid[4] in pids:
    klass=prop(win,atoms['WM_CLASS'],256);title=prop(win,atoms['_NET_WM_NAME'],256) or prop(win,atoms['WM_NAME'],256)
    geomroot=W();gx=I();gy=I();width=U();height=U();border=U();bits=U()
    ok=x.XGetGeometry(display,win,ctypes.byref(geomroot),ctypes.byref(gx),ctypes.byref(gy),ctypes.byref(width),ctypes.byref(height),ctypes.byref(border),ctypes.byref(bits)) and safe_sync()
    rows.append({'window':hex(win),'pid':pid[4],'wm_class_hex':klass[4].hex() if klass and klass[1]==8 else None,'wm_class_truncated':bool(klass and klass[3]),'title_hex':title[4].hex() if title and title[1]==8 else None,'title_truncated':bool(title and title[3]),'geometry':{'width':width.value,'height':height.value,'border':border.value} if ok else None})
   if depth>=32:continue
   root_id=W();parent=W();children=ctypes.POINTER(W)();n=U()
   result=x.XQueryTree(display,win,ctypes.byref(root_id),ctypes.byref(parent),ctypes.byref(children),ctypes.byref(n));ok=safe_sync()
   try:
    if result and ok:
     if n.value>10000 or len(queue)+n.value>10000:raise RuntimeError('X child list exceeded bound')
     queue.extend((int(children[i]),depth+1) for i in range(n.value))
   finally:
    if children:x.XFree(children)
  return rows
 finally:x.XCloseDisplay(display)

def diagnostic_first_launch():
 child,ident=start('normal')
 def snapshot(filename):
  pids=set(child.inspector.members(child.pid));pids.add(child.pid)
  result={'browser_pid':child.pid,'webapp_id':ident,'owned_session_pids':sorted(pids),'helper_list':[],'scope':'read-only _NET_WM_PID-matched X11 windows; no input or screenshot'}
  # Persist identity even if a helper fails or the page never appears.
  path=evidence/filename
  path.write_text(json.dumps(result,indent=2)+'\n')
  for pid in sorted(pids):
   try:
    r=subprocess.run([str(a.helper),str(pid),'WebApp-'+ident,'list'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
    result['helper_list'].append({'pid':pid,'exit':r.returncode,'stdout':r.stdout[:8192],'stderr':r.stderr[:2048]})
   except subprocess.TimeoutExpired:
    result['helper_list'].append({'pid':pid,'error':'helper timeout'})
  path.write_text(json.dumps(result,indent=2)+'\n')
  return result
 snapshot('owned-windows-start.json')
 wait_for(lambda:pageshow('/a','normal'),'first pageshow')
 time.sleep(10)
 result=snapshot('owned-windows.json')
 try:result['owned_windows']=inspect_owned_windows(set(result['owned_session_pids']))
 finally:(evidence/'owned-windows.json').write_text(json.dumps(result,indent=2)+'\n')
 return result

def window_for(child,ident,expected_title=None):
 def lookup():
  if child.poll() is not None:raise RuntimeError('application exited before window')
  text=ui(child.pid,ident,'list');rows=[x for x in text.splitlines() if 'mapped=1' in x]
  if len(rows)>1:raise RuntimeError('ambiguous matching windows')
  if not rows:return None
  m=re.search(r'^window=(0x[0-9a-fA-F]+) .*width=(\d+) height=(\d+) title_hex=([0-9a-fA-F]*)$',rows[0]);
  if not m:return None
  if int(m.group(2))<640 or int(m.group(3))<480+a.content_offset_y:raise RuntimeError('window too small for calibrated fixture')
  title=bytes.fromhex(m.group(4)).decode('utf-8','replace')
  if expected_title is not None and title!=expected_title:return None
  return (m.group(1),title)
 return wait_for(lookup,'visible mapped window'+(' with title '+repr(expected_title) if expected_title is not None else ''))
def stop(child):
 child.stop()
 if child.alive():raise RuntimeError('owned process session remains')
def graceful(child,ident,window):
 ui(child.pid,ident,'close',window=window)
 try:
  wait_for(lambda:child.poll() is not None,'graceful app close')
  wait_for(lambda:not child.alive(),'graceful session cleanup')
 except TimeoutError:
  pids=set(child.inspector.members(child.pid));pids.add(child.pid)
  info={'browser_pid':child.pid,'webapp_id':ident,'window':window,'owned_session_pids':sorted(pids)}
  try:info['owned_windows']=inspect_owned_windows(pids)
  except Exception as exc:info['inspection_error']=str(exc)
  path=evidence/('close-timeout-'+str(child.pid)+'.json')
  path.write_text(json.dumps(info,indent=2)+'\n')
  raise

def record(name,fn):
 try: cases[name]={'status':'PASS','detail':fn()}
 except Exception as e:cases[name]={'status':'FAIL','detail':str(e)};raise
try:
 def invalid_args():
  log=(evidence/'invalid-args.log').open('xb',buffering=0);logs.append(log)
  bad=OwnedProcessGroup([str(a.browser),'--webapp-id=../escape','--webapp-url='+path_url('invalid'),'--webapp-name=Invalid'],cwd=str(root),env=env,stdout=log,stderr=log)
  bad.start();owned.append(bad);code=wait_for(lambda:(True,bad.poll()) if bad.poll() is not None else None,'invalid argument exit')
  code=code[1]
  if code==0:raise AssertionError('invalid ID accepted')
  stop(bad)
  if (root/'escape').exists() or (root/'config/Ember Browser/webapps').exists():raise AssertionError('invalid ID created profile')
  return 'invalid ID exits nonzero before creating profile'
 record('invalid_args',invalid_args)
 if a.diagnostic_only:
  cases['window_diagnostic']={'status':'OBSERVED','detail':diagnostic_first_launch()}
  raise SystemExit(0)
 def normal_start():
  c,i=start('normal');w,title=window_for(c,i,expected_title='QA normal');wait_for(lambda:seen('/a','normal'),'normal A');return c,i,w,title
 c,ident,win,title=normal_start();assert title=='QA normal', 'unexpected native title: '+title;wait_for(lambda:pageshow('/a','normal'),'initial pageshow');ui(c.pid,ident,'screenshot',str(evidence/'window-before-input.ppm'),window=win);cases['normal_launch']={'status':'PASS','window':win,'title':title,'content_offset_y':a.content_offset_y,'note':'mapped; inspect screenshot before interpreting coordinates'}
 def busy_clear():
  profile=root/'config/Ember Browser/webapps'/ident
  marker=profile/'qa-clear-sentinel';marker.write_text('keep-while-active')
  private=root/'config/Ember Browser/webapps-private'/ident;private.mkdir(parents=True);(private/'qa-clear-sentinel').write_text('private')
  other=root/'config/Ember Browser/webapps/qa_other_sentinel';other.mkdir(parents=True);(other/'keep').write_text('other')
  lock=root/'config/Ember Browser/webapp-locks'/ident
  fd=os.open(lock,os.O_RDWR|os.O_NOFOLLOW)
  try:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:pass
   else:raise AssertionError('active process did not retain shared flock')
  finally:os.close(fd)
  r=subprocess.run([str(a.browser),'--webapp-clear='+ident],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
  assert 'Close this web app' in r.stderr
  assert r.returncode != 0 and marker.read_text()=='keep-while-active' and (private/'qa-clear-sentinel').read_text()=='private' and c.poll() is None and c.alive()
  return 'active session rejected clear; profile and process retained'
 record('busy_clear',busy_clear)
 def same_id():
  second,_=start('same',ident=ident,url=path_url('normal',setcookie=True));wait_for(lambda:second.poll() is not None,'second launch exit');
  if second.poll()!=0:raise AssertionError('same-ID second launch failed')
  stop(second)
  rows=ui(c.pid,ident,'list');assert len([x for x in rows.splitlines() if 'mapped=1' in x])==1
  return 'same process window count=1; focus still requires visual confirmation'
 record('same_id',same_id)
 def nav():
  # The fixture link is a regular anchor; coordinate is checked against target window by helper.
  ui(c.pid,ident,'click',55,90+a.content_offset_y,window=win);wait_for(lambda:pageshow('/b','normal'),'fixture B pageshow');ui(c.pid,ident,'key','Alt+Left',window=win);wait_for(lambda:pageshow('/a','normal',2),'back A pageshow');ui(c.pid,ident,'key','Ctrl+r',window=win);wait_for(lambda:pageshow('/a','normal',3),'reload A pageshow');return 'click B, Back and Reload confirmed by pageshow counters'
 record('navigation',nav)
 def isolate():
  b,j=start('other');bw,_=window_for(b,j);rows=wait_for(lambda:seen('/a','other'),'other profile');assert all('webapp_qa=normal' not in x['cookie'] for x in rows);graceful(b,j,bw);return 'second ID did not send first ID cookie'
 record('different_id',isolate)
 def private_restart():
  pc,pi=start('private',private=True);pw,_=window_for(pc,pi);first=wait_for(lambda:seen('/a','private'),'private initial');assert all('webapp_qa=normal' not in x['cookie'] for x in first)
  wait_for(lambda:pageshow('/a','private'),'private initial pageshow')
  wait_for(lambda:any('webapp_qa=private' in x['cookie'].split('; ') for x in (pageshow('/a','private') or [])),'private cookie observed')
  graceful(pc,pi,pw)
  with event_lock:baseline=sum(e['path']=='/a' and e['tag']=='private' for e in events)
  again,_=start('private-restart',private=True,ident=pi,url=path_url('private',setcookie=True));aw,_=window_for(again,pi);rows=wait_for(lambda:seen('/a','private',baseline+1),'private restart');assert 'webapp_qa=private' not in rows[baseline]['cookie'].split('; ');graceful(again,pi,aw);return 'cookie observed before close and absent on first private restart request'
 record('private_cookie_restart',private_restart)
 # A screenshot is evidence for human review, not an automated text/visibility PASS.
 ui(c.pid,ident,'screenshot',str(evidence/'window.ppm'),window=win);cases['visible_content']={'status':'REVIEW','detail':'inspect captured target Composite pixmap; no OCR PASS'}
 def normal_restart():
  global c,win
  graceful(c,ident,win)
  with event_lock:
   baseline=sum(e['path']=='/a' and e['tag']=='normal' for e in events)
   show_baseline=sum(e['path']=='/seen' and e['tag']=='normal' and e['page']=='/a' for e in events)
  again,_=start('normal-restart',ident=ident,url=path_url('normal',setcookie=True));aw,_=window_for(again,ident)
  rows=wait_for(lambda:seen('/a','normal',baseline+1),'normal restart')
  assert 'webapp_qa=normal' in rows[baseline]['cookie'].split('; '), 'normal cookie absent on first restart request'
  wait_for(lambda:pageshow('/a','normal',show_baseline+1),'normal restart pageshow')
  c,win=again,aw
  return 'persistent cookie present on first request after normal restart'
 record('normal_cookie_restart',normal_restart)
 def popup():
  ui(c.pid,ident,'click',55,150+a.content_offset_y,window=win);wait_for(lambda:seen('/popup','normal'),'popup request');wait_for(lambda:seen('/opener-confirm','normal'),'popup opener callback');return 'popup page sent postMessage to opener, which verified source, origin and nonce'
 record('popup_request',popup)
 def graceful_all():
  pids=set(c.inspector.members(c.pid));pids.add(c.pid)
  windows=[]
  for pid in sorted(pids):
   for line in ui(pid,ident,'list').splitlines():
    if 'mapped=1' in line:
     m=re.match(r'^window=(0x[0-9a-fA-F]+) ',line)
     if not m:raise RuntimeError('invalid scoped window listing')
     windows.append((pid,m.group(1)))
  if (c.pid,win) not in windows:raise RuntimeError('main window missing during graceful shutdown')
  for pid,window in windows:
   if (pid,window)!=(c.pid,win):ui(pid,ident,'close',window=window)
  graceful(c,ident,win)
  assert all(not child.alive() for child in owned), 'owned session still active'
  return 'owned mapped windows closed; main session exited'
 record('graceful_all',graceful_all)
 def clear_after_exit():
  r=subprocess.run([str(a.browser),'--webapp-clear='+ident],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
  assert r.returncode==0, r.stderr[:300]
  base=root/'config/Ember Browser'
  assert not (base/'webapps'/ident).exists() and not (base/'webapps-private'/ident).exists()
  assert (base/'webapps/qa_other_sentinel/keep').read_text()=='other' and ordinary_hashes()==ordinary_before
  return 'both ID profiles absent; other ID and ordinary sentinels retained'
 record('clear_after_exit',clear_after_exit)
 cases['popup_opener']={'status':'PASS','detail':'same-origin popup-to-opener message verified; popup visibility and OAuth navigation remain untested'}
 cases['native_menu_tabs']={'status':'NOT_RUN','detail':'requires target layout and selectable-tab assertion'}
 record('ordinary_profile_sentinel',lambda: 'seeded Local State and GPUCache unchanged' if ordinary_hashes()==ordinary_before else (_ for _ in ()).throw(AssertionError('ordinary profile sentinel changed')))
 cases['ordinary_profile_full']={'status':'NOT_RUN','detail':'sentinels only; real profile deliberately not accessed'}
finally:
 errors=[]
 for child in reversed(owned):
  try:stop(child)
  except Exception as exc:errors.append(str(exc))
 for f in logs:f.close()
 try:
  if ordinary_hashes()!=ordinary_before:raise AssertionError('ordinary sentinel changed after exit')
  cases['ordinary_profile_after_exit']={'status':'PASS','detail':'seeded files unchanged through owned process cleanup'}
 except Exception as exc:
  cases['ordinary_profile_after_exit']={'status':'FAIL','detail':str(exc)};errors.append('ordinary profile sentinel changed')
 server.shutdown();server.server_close();thread.join(timeout=5)
 with event_lock:snapshot=list(events)
 (evidence/'events.json').write_text(json.dumps(snapshot,indent=2)+'\n');(evidence/'result.json').write_text(json.dumps({'cases':cases,'cleanup_errors':errors},indent=2)+'\n')
 if not errors:
  current=root.lstat()
  if (current.st_dev,current.st_ino)==(rootstat.st_dev,rootstat.st_ino) and root.parent==Path('/var/tmp') and root.name.startswith('ember-webapp-qa-'):shutil.rmtree(root)
 if errors:raise SystemExit('owned process cleanup failed; test profile retained')
print(json.dumps({'cases':cases,'evidence':str(evidence)}))
