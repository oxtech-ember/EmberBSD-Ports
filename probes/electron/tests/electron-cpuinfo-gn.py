#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify CPUINFO's source shim and both simultaneously populated GN roles."""
import argparse,json,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for n in ('source','gn','patch-tool'): p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();src=a.source.resolve(strict=True);gn=str(a.gn.resolve(strict=True));patch=Path(__file__).resolve().parents[1]/'patches/gn-common-cpuinfo.patch'
codecpatch=(patch.parent/'gn-common-codecs.patch').read_text().split('+++ b/build/config/emberbsd_codecs.gni\n',1)[1]
gni=''.join(line[1:] for line in codecpatch.splitlines(True)[1:] if line.startswith('+'))
with tempfile.TemporaryDirectory() as td:
 root=Path(td).resolve()
 def put(path,data):
  f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(data)
 f=root/'build/linux/unbundle/replace_gn_files.py';f.parent.mkdir(parents=True);f.write_bytes((src/'build/linux/unbundle/replace_gn_files.py').read_bytes())
 tflite=root/'third_party/tflite/BUILD.gn';tflite.parent.mkdir(parents=True);shutil.copy2(src/'third_party/tflite/BUILD.gn',tflite)
 assert 'if (!emberbsd_common_cpuinfo)' not in tflite.read_text()
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=root,check=True,capture_output=True)
 assert 'if (!emberbsd_common_cpuinfo)' in tflite.read_text()
 fragment = tflite.read_text().split('if (!emberbsd_common_cpuinfo) {', 1)[1].split('}', 1)[0]
 assert 'include_dirs = [ "//third_party/cpuinfo/src" ]' in fragment
 assert "'cpuinfo': 'third_party/cpuinfo/BUILD.gn'" in f.read_text()
 put('build/config/emberbsd_codecs.gni',gni)
 put('.gn','buildconfig="//config.gn"\n')
 put('build/shim_headers.gni','template("shim_headers") { not_needed(invoker, "*") source_set(target_name) {} }\n')
 put('build/config/linux/pkg_config.gni','template("pkg_config") { assert(invoker.ignore_libs) not_needed(invoker, "*") config(target_name) { include_dirs=["//selected-headers"] } }\n')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } }\nsource_set("test") { deps=["//skia:test","//third_party/tflite:include_check"] }\n')
 put('third_party/tflite/BUILD.gn', 'import("//build/config/emberbsd_cpuinfo.gni")\nsource_set("include_check") { if (!emberbsd_common_cpuinfo) {' + fragment + '} }\n')
 put('skia/BUILD.gn','source_set("test") { deps=["//third_party/cpuinfo:cpuinfo"] }\n')
 (root/'third_party/cpuinfo').mkdir(parents=True);shutil.copy2(root/'build/linux/unbundle/cpuinfo.gn',root/'third_party/cpuinfo/BUILD.gn')
 for role in ('native','target'):
  put('config.gn',f'set_default_toolchain("//:tc")\nemberbsd_pkg_config_role="{role}"\n')
  out=root/('out-'+role);out.mkdir();selected='host' if role=='native' else 'target'
  args='emberbsd_common_cpuinfo=true\n'+''.join(f'emberbsd_cpuinfo_{r}_{kind}=["{root}/{r}-{kind}"]\n' for r in ('host','target') for kind in ('libraries','inputs'))
  (out/'args.gn').write_text(args)
  for r in ('host','target'):
   for kind in ('libraries','inputs'): (root/(r+'-'+kind)).write_text('fixture')
  run=subprocess.run([gn,'gen',str(out),'--fail-on-unused-args'],cwd=root,text=True,capture_output=True)
  if run.returncode:raise RuntimeError(run.stdout+run.stderr)
  label='//third_party/cpuinfo:emberbsd_cpuinfo';info=json.loads(subprocess.check_output([gn,'desc',str(out),label,'--format=json'],cwd=root,text=True))[label]
  assert info['libs']==['//'+selected+'-libraries'] and info['inputs']==['//'+selected+'-inputs']
  assert info['ldflags']==[('-Wl,-rpath,'+str(root) if role=='native' else '-Wl,-rpath=/usr/pkg/lib')]
  include=json.loads(subprocess.check_output([gn,'desc',str(out),'//third_party/tflite:include_check','--format=json'],cwd=root,text=True))['//third_party/tflite:include_check']
  assert all('third_party/cpuinfo/src' not in p for p in include.get('include_dirs', []))
  info=json.loads(subprocess.check_output([gn,'desc',str(out),'//skia:test','--format=json'],cwd=root,text=True))['//skia:test']
  assert info['libs']==['//'+selected+'-libraries'] and '//selected-headers/' in info['include_dirs']
 # Bundled selection keeps the original TFLite include without loading the common wrapper.
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } }\nsource_set("test") { deps=["//third_party/tflite:include_check"] }\n')
 out_bundled=root/'out-bundled';out_bundled.mkdir()
 (out_bundled/'args.gn').write_text('emberbsd_common_cpuinfo=false\n')
 subprocess.run([gn,'gen',str(out_bundled),'--fail-on-unused-args'],cwd=root,check=True,capture_output=True)
 bundled=json.loads(subprocess.check_output([gn,'desc',str(out_bundled),'//third_party/tflite:include_check','--format=json'],cwd=root,text=True))['//third_party/tflite:include_check']
 assert '//third_party/cpuinfo/src/' in bundled['include_dirs']
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } }\nsource_set("test") { deps=["//skia:test"] }\n')
 out=root/'out-target';args=out/'args.gn';args.write_text(args.read_text().replace(
  f'emberbsd_cpuinfo_target_libraries=["{root}/target-libraries"]','emberbsd_cpuinfo_target_libraries=[]'))
 run=subprocess.run([gn,'gen',str(out),'--fail-on-unused-args'],cwd=root,text=True,capture_output=True)
 assert run.returncode and 'Selected codec provider is incomplete' in (run.stdout+run.stderr)
print('PASS: CPUINFO shim, simultaneous role inputs and strict selected provider')
