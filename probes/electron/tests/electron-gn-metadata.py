# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse,importlib.util,os,shutil,subprocess,sys,tempfile
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True);parser.add_argument('--git',type=Path,required=True)
a=parser.parse_args();assert a.source.is_absolute() and a.git.is_absolute()
repo=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files';up=a.source;python=sys.executable;git=str(a.git)
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('controller',repo/'build-electron.py');v=load('view',repo/'protobuf-source-view.py')
with tempfile.TemporaryDirectory() as d:
 w=Path(d);src=w/'workspace/src';(src/'build/util').mkdir(parents=True)
 for f in ['build/util/lastchange.py','build/compute_build_timestamp.py']:
  shutil.copy2(up/f,src/f)
 (src/'third_party').mkdir();(src/'third_party/depot_tools').symlink_to(up/'third_party/depot_tools',target_is_directory=True)
 for f in ['third_party/dawn','third_party/skia','gpu/webgpu','skia/ext','gpu/config']:(src/f).mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,PATH=str(Path(python).parent)+':'+str(Path(git).parent)+':/bin',EMBERBSD_CONTROL_GIT=git,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_AUTHOR_NAME='test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='test',GIT_COMMITTER_EMAIL='test@example.invalid')
 subprocess.run([git,'init','-q'],cwd=src,env=env,check=True);subprocess.run([git,'add','build'],cwd=src,env=env,check=True);subprocess.run([git,'commit','-qm','fixture\n\nChange-Id: Iabc'],cwd=src,env=env,check=True)
 dest=w/'view';(dest/'src').mkdir(parents=True);v.mirror(src/'build',dest/'src/build')
 consumer=dest/'src/build/compute_build_timestamp.py'
 before=subprocess.run([python,'-B',str(consumer),'official'],capture_output=True,env=env);assert before.returncode and b'LASTCHANGE.committime' in before.stderr
 class Native:
  def tool(self,n): assert n=='python';return python
 class Proc:
  @staticmethod
  def capture(argv,**kwargs):return subprocess.run(argv,check=True,stdout=subprocess.PIPE,**kwargs)
 m.ensure_lastchange(w/'workspace',Native(),env,{'process':Proc})
 def verify(source,protobuf,destination,*,_updates=None,_refresh=False,**kw):v.mirror(source/'build',destination/'src/build',verify=True,updates=_updates);return destination/'src'
 v.verify=verify;v._refresh_leaves(src,None,dest,{})
 after=subprocess.run([python,'-B',str(consumer),'official'],capture_output=True,env=env);assert after.returncode==0,(after.stdout,after.stderr)
 print('PASS real lastchange + view refresh + Chromium timestamp consumer')
