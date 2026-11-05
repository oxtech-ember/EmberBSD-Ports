#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify system OpenH264 label aliases and both selected toolchain roles."""
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for n in ('source','gn','patch-tool'): p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args(); src=a.source.resolve(strict=True); gn=str(a.gn.resolve(strict=True))
patch=Path(__file__).resolve().parents[1]/'patches/gn-common-openh264.patch'
codecpatch=(patch.parent/'gn-common-codecs.patch').read_text().split('+++ b/build/config/emberbsd_codecs.gni\n',1)[1]
gni=''.join(line[1:] for line in codecpatch.splitlines(True)[1:] if line.startswith('+'))
with tempfile.TemporaryDirectory() as td:
 r=Path(td).resolve()
 def put(path,data):
  f=r/path; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(data)
 f=r/'build/linux/unbundle/openh264.gn';f.parent.mkdir(parents=True);f.write_bytes((src/'build/linux/unbundle/openh264.gn').read_bytes())
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=r,check=True,capture_output=True)
 put('build/config/emberbsd_codecs.gni',gni)
 put('.gn','buildconfig="//config.gn"\n')
 put('build/shim_headers.gni','template("shim_headers") { not_needed(invoker, "*") source_set(target_name) {} }\n')
 put('build/config/linux/pkg_config.gni','template("pkg_config") { assert(invoker.ignore_libs) not_needed(invoker, "*") config(target_name) { include_dirs=["//selected-headers"] } }\n')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } }\nsource_set("test") { deps=['+','.join('"//third_party/openh264:'+x+'"' for x in ('common','processing','encoder','decoder'))+'] }\n')
 (r/'third_party/openh264').mkdir(parents=True);shutil.copy2(f,r/'third_party/openh264/BUILD.gn')
 for role in ('native','target'):
  put('config.gn',f'set_default_toolchain("//:tc")\nemberbsd_pkg_config_role="{role}"\nis_clang=false\n')
  out=r/('out-'+role);out.mkdir();selected='host' if role=='native' else 'target'
  (out/'args.gn').write_text('emberbsd_common_openh264=true\n'+''.join(f'emberbsd_openh264_{selected}_{k}=["{r}/{k}"]\n' for k in ('libraries','inputs')))
  for k in ('libraries','inputs'): (r/k).write_text('fixture')
  run=subprocess.run([gn,'gen',str(out),'--fail-on-unused-args'],cwd=r,text=True,capture_output=True)
  if run.returncode: raise RuntimeError(run.stdout+run.stderr)
  label='//third_party/openh264:emberbsd_openh264'
  info=json.loads(subprocess.check_output([gn,'desc',str(out),label,'--format=json'],cwd=r,text=True))[label]
  assert info['libs']==['//libraries'] and info['inputs']==['//inputs']
  assert info['ldflags']==['-Wl,-rpath='+ (str(r) if role=='native' else '/usr/pkg/lib')]
  aggregate=json.loads(subprocess.check_output([gn,'desc',str(out),'//:test','--format=json'],cwd=r,text=True))['//:test']
  assert aggregate['libs']==['//libraries'] and '//selected-headers/' in aggregate['include_dirs']
print('PASS: OpenH264 labels use selected role inputs, headers and rpath')
