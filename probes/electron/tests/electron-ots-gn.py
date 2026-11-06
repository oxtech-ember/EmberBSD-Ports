#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check current OTS sources are enabled without changing bundled GN policy."""
import argparse,json,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for n in ('source','gn','patch-tool'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();src=a.source.resolve(strict=True);gn=str(a.gn.resolve(strict=True));patch=Path(__file__).resolve().parents[1]/'patches/gn-common-ots.patch'
with tempfile.TemporaryDirectory(prefix='ots-gn-') as tmp:
 root=Path(tmp).resolve()
 def put(path,data):
  f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(data)
 put('third_party/ots/BUILD.gn',(src/'third_party/ots/BUILD.gn').read_text())
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=root,check=True,capture_output=True)
 put('.gn','buildconfig="//config.gn"\n');put('config.gn','set_default_toolchain("//:tc")\nset_defaults("static_library") { configs=["//build/config/compiler:chromium_code"] }\n')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="unused" } tool("alink") { command="unused" outputs=["{{target_out_dir}}/{{target_output_name}}.a"] } }\ngroup("all") { deps=["//third_party/ots"] }\n')
 put('testing/libfuzzer/fuzzer_test.gni','template("fuzzer_test") { not_needed(invoker, "*") group(target_name) { testonly=true } }\n')
 put('build/config/compiler/BUILD.gn','config("chromium_code") {}\nconfig("no_chromium_code") {}\n')
 for n,label in (('brotli','dec'),('woff2','woff2_dec'),('zlib','zlib')):put('third_party/'+n+'/BUILD.gn','group("'+label+'") {}\n')
 infos=[]
 for enabled in (False,True):
  out=root/('on' if enabled else 'off');out.mkdir();(root/'identity').write_text('fixture');(out/'args.gn').write_text('emberbsd_common_ots='+str(enabled).lower()+'\n'+('emberbsd_ots_identity="//identity"\n' if enabled else ''))
  result=subprocess.run([gn,'gen',str(out),'--fail-on-unused-args'],cwd=root,text=True,capture_output=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  info=json.loads(subprocess.check_output([gn,'desc',str(out),'//third_party/ots:ots','--format=json'],cwd=root,text=True))['//third_party/ots:ots'];infos.append(info)
 before,after=(set(i['sources']) for i in infos)
 assert after-before=={'//third_party/ots/src/src/colr.cc','//third_party/ots/src/src/cpal.cc'} and not before-after
 assert infos[0].get('defines',[])==infos[1].get('defines',[])
 assert infos[1]['inputs']==['//identity']
print('PASS: OTS 9.3 source delta is opt-in and preserves bundled compile defines')
