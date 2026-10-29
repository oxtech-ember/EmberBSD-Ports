#!/usr/bin/env python3
"""Verify selected Darwin echo in pkg_tarup, including privilege prompting."""
import argparse, os, pathlib, subprocess, tempfile
p=argparse.ArgumentParser()
for name in ('pkg-tarup','pkg-info','shell','pkgdb'):
 p.add_argument('--'+name,type=pathlib.Path,required=True)
p.add_argument('--package',required=True)
a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='pkg-tarup-echo-') as tmp:
 root=pathlib.Path(tmp); archive=root/'archives';archive.mkdir()
 env=dict(os.environ)
 for key in ('ECHO','ECHO_N','ID','SU_CMD','HEAD','SED','GREP','XARGS','ROOT_USER','PKG_DESTDIR','PKG_PATH'):
  env.pop(key,None)
 r=subprocess.run([str(a.pkg_tarup),'-K',str(a.pkgdb),'-d',str(archive),a.package],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 assert r.returncode==0,(r.stdout,r.stderr)
 assert not r.stderr,r.stderr
 archives=list(archive.glob('*.tgz'));assert len(archives)==1,archives
 info=subprocess.run([str(a.pkg_info),'-qf',str(archives[0])],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True)
 assert '@name '+a.package+'\n' in info.stdout,info.stdout
 mock_id=root/'mock-id';mock_id.write_text('#!'+str(a.shell)+'\nif [ "$#" -gt 1 ]; then echo 0; else echo 1000; fi\n');mock_id.chmod(0o755)
 mock_su=root/'mock-su';mock_su.write_text('#!'+str(a.shell)+'\nwhile IFS= read -r line; do :; done\nexit 0\n');mock_su.chmod(0o755)
 prompt_env=dict(env,ID=str(mock_id),SU_CMD=str(mock_su),ROOT_USER='root')
 r=subprocess.run([str(a.pkg_tarup),'ignored'],env=prompt_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)
 assert r.stdout.endswith(str(mock_su)+' '),repr(r.stdout)
 custom=root/'echo-n';custom.write_text('#!'+str(a.shell)+'\nprintf "override:%s" "$1"\n');custom.chmod(0o755)
 r=subprocess.run([str(a.pkg_tarup),'ignored'],env=dict(prompt_env,ECHO_N=str(custom)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 assert r.returncode==0 and not r.stderr and r.stdout.endswith('override:'+str(mock_su)+' '),(r.stdout,r.stderr)
 print('PASS: actual package archive and non-root prompt with selected echo')
