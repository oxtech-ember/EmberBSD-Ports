#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify the real Chromium target binds the selected LevelDB receipt."""
import argparse, json, subprocess, tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('source','gn','patch-tool'): p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); source=a.source.resolve(strict=True); patch=Path(__file__).resolve().parents[1]/'patches/gn-common-leveldb.patch'
with tempfile.TemporaryDirectory(prefix='electron-leveldb-gn-') as td:
 root=Path(td)
 def put(name,data):
  path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
 build=(source/'third_party/leveldatabase/BUILD.gn').read_text()
 put('third_party/leveldatabase/BUILD.gn',build)
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=root,check=True,capture_output=True)
 path=root/'third_party/leveldatabase/BUILD.gn'; text=path.read_text().split('# leveldb does not mark symbols',1)[0];path.write_text(text)
 put('.gn','buildconfig="//config.gn"\n')
 put('config.gn','''set_default_toolchain("//:tc")
is_component_build=false
is_win=false
is_official_build=false
template("component") { static_library(target_name) { forward_variables_from(invoker, "*") } }
set_defaults("component") { configs=["//build/config/compiler:chromium_code"] }
''')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="unused" } tool("alink") { command="unused" outputs=["{{target_out_dir}}/{{target_output_name}}.a"] } }\ngroup("all") { deps=["//third_party/leveldatabase"] }\n')
 for n in ('testing/libfuzzer/fuzzer_test.gni','testing/test.gni'):put(n,'')
 put('build/config/compiler/BUILD.gn','config("chromium_code") {}\nconfig("no_chromium_code") {}\n')
 for n,target in (('base','base'),('build','chromeos_buildflags'),('components/services/storage/public/cpp/filesystem','filesystem'),('third_party/crc32c','crc32c'),('third_party/re2','re2'),('third_party/snappy','snappy')):
  put(n+'/BUILD.gn','group("'+target+'") {}\n')
 # Absolute label //base selects its default target.
 put('identity','receipt')
 infos=[]
 for enabled in (False,True):
  out=root/('on' if enabled else 'off');out.mkdir();(out/'args.gn').write_text('emberbsd_common_leveldb='+str(enabled).lower()+'\n'+('emberbsd_leveldb_identity="//identity"\n' if enabled else ''))
  run=subprocess.run([str(a.gn),'gen',str(out),'--fail-on-unused-args'],cwd=root,text=True,capture_output=True)
  if run.returncode:raise RuntimeError(run.stdout+run.stderr)
  info=json.loads(subprocess.check_output([str(a.gn),'desc',str(out),'//third_party/leveldatabase:leveldatabase','--format=json'],cwd=root,text=True))['//third_party/leveldatabase:leveldatabase'];infos.append(info)
 assert infos[0]['sources']==infos[1]['sources']
 assert infos[0].get('inputs',[])==[] and infos[1]['inputs']==['//identity']
 assert infos[0].get('defines',[])==infos[1].get('defines',[])
print('PASS: Chromium LevelDB target binds selected receipt and preserves source list and defines')
