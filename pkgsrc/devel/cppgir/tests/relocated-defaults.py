import os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Exercise CppGir after prefix relocation')
parser.add_argument('--binary',type=Path,required=True)
parser.add_argument('--data',type=Path,required=True)
parser.add_argument('--gir-dir',type=Path,required=True)
parser.add_argument('--sdk-prefix',type=Path,required=True)
parser.add_argument('--old-archive',type=Path,help='optional negative control')
a=parser.parse_args()
p=a.sdk_prefix;source=a.binary;data=a.data;old=a.old_archive;fixture=Path(__file__).with_name('strict-gir.py')
with tempfile.TemporaryDirectory(prefix='ember-cppgir-relocated-') as tmp:
 root=Path(tmp);new=root/'new';previous=root/'old'
 for d in (new,previous):
  (d/'bin').mkdir(parents=True);(d/'share/cppgir').mkdir(parents=True);(d/'share/gir-1.0').mkdir(parents=True)
  for f in data.iterdir():
   if f.is_file():shutil.copy2(f,d/'share/cppgir'/f.name)
  for f in a.gir_dir.glob('*.gir'):shutil.copy2(f,d/'share/gir-1.0'/f.name)
  shutil.copy2(d/'share/gir-1.0/Gio-2.0.gir',d/'share/gir-1.0/RelocProbe-1.0.gir')
 shutil.copy2(source,new/'bin/cppgir')
 if old:
  with tarfile.open(old) as t:
   m=next(x for x in t if x.name.lstrip('./')=='bin/cppgir');(previous/'bin/cppgir').write_bytes(t.extractfile(m).read());(previous/'bin/cppgir').chmod(0o755)
 env=os.environ.copy()
 for k in ('GI_GIR','GI_GIR_PATH','GI_IGNORE','XDG_DATA_DIRS'):env.pop(k,None)
 env['XDG_DATA_HOME']=str(root/'empty');env['PATH']=str(new/'bin')+':'+str(p/'bin')+':'+str(p/'gnu')
 def run(name,args,ok):
  out=root/('out-'+name);out.mkdir();r=subprocess.run(args+['--debug','4','--class','--expected','--output',str(out),'RelocProbe-1.0'],env=env,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  if (r.returncode==0)!=ok:raise SystemExit(name+' unexpected '+str(r.returncode)+'\n'+r.stdout[-2500:])
  if ok and (str(new/'share/gir-1.0') not in r.stdout):raise SystemExit(name+' no relocated GIR path in log\n'+r.stdout[-1200:])
  print(name,'PASS')
 if old: run('old-negative',[str(previous/'bin/cppgir')],False)
 run('absolute',[str(new/'bin/cppgir')],True)
 run('PATH',['cppgir'],True)
 (root/'alias').symlink_to(new/'bin/cppgir');run('symlink',[str(root/'alias')],True)
 for f in (new/'share/cppgir').iterdir(): f.unlink()
 out=root/'out-missing-ignore';out.mkdir()
 r=subprocess.run([str(new/'bin/cppgir'),'--output',str(out),'RelocProbe-1.0'],env=env,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if r.returncode == 0 or 'required default ignore file location not specified' not in r.stdout: raise SystemExit('missing relocated ignore: unexpected result '+str(r.returncode)+'\n'+r.stdout[-1500:])
 print('relocated ignore required PASS')
 for f in data.iterdir():
  if f.is_file():shutil.copy2(f,new/'share/cppgir'/f.name)
 target=a.gir_dir;host=a.gir_dir
 r=subprocess.run([str(p/'bin/python3.15'),'-B','-E','-S',str(fixture),str(new/'bin/cppgir'),str(new/'share/cppgir'),str(target),str(host)],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit('strict FAIL\n'+r.stdout[-2500:])
 print(r.stdout.strip());print('fixtures PASS')
