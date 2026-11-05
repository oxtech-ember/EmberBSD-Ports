#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise common codec wrappers and role-specific link inputs in GN."""
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for n in ('source','gn','patch-tool'): p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args(); src=a.source.resolve(strict=True); gn=str(a.gn.resolve(strict=True))
patch=Path(__file__).resolve().parents[1]/'patches/gn-common-codecs.patch'
names={'dav1d':'dav1d','libaom':'aom','libvpx':'vpx','opus':'opus','flac':'flac'}
with tempfile.TemporaryDirectory() as td:
 r=Path(td).resolve()
 def put(path,data):
  f=r/path; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(data)
 for name in [*(f'build/linux/unbundle/{x}.gn' for x in names),'media/base/BUILD.gn','media/base/libaom_thread_wrapper.cc','media/base/libvpx_thread_wrapper.cc']:
  f=r/name; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes((src/name).read_bytes())
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=r,check=True,capture_output=True)
 put('.gn','buildconfig="//config.gn"\n')
 put('build/shim_headers.gni','template("shim_headers") { not_needed(invoker, "*") config("${target_name}_config") {} source_set(target_name) { all_dependent_configs=[":${target_name}_config"] } }\n')
 put('build/config/linux/pkg_config.gni','template("pkg_config") { assert(invoker.ignore_libs) not_needed(invoker, "*") config(target_name) { include_dirs=["//selected-headers"] } }\n')
 put('build/buildflag_header.gni','template("buildflag_header") { not_needed(invoker, "*") source_set(target_name) {} }\n')
 put('third_party/libaom/options.gni','enable_libaom=true\n')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } }\nsource_set("test") { deps=['+','.join('"//third_party/'+x+':'+x+'"' for x in names)+'] }\n')
 for name in names:
  f=r/'third_party'/name/'BUILD.gn'; f.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(r/'build/linux/unbundle'/f'{name}.gn',f)
 for role in ('native','target'):
  put('config.gn',f'set_default_toolchain("//:tc")\nemberbsd_pkg_config_role="{role}"\n')
  out=r/('out-'+role);out.mkdir();selected='host' if role=='native' else 'target'
  (out/'args.gn').write_text('emberbsd_common_codecs=true\n'+''.join(f'emberbsd_{n}_{item_role}_{k}=["{r}/{item_role}/{n}-{k}"]\n' for n in names.values() for k in ('libraries','inputs') for item_role in ('host','target')))
  for item_role in ('host','target'):
   (r/item_role).mkdir(exist_ok=True)
   for name in names.values():
    for kind in ('libraries','inputs'): (r/item_role/(name+'-'+kind)).write_text('fixture')
  run=subprocess.run([gn,'gen',str(out),'--fail-on-unused-args'],cwd=r,text=True,capture_output=True)
  if run.returncode: raise RuntimeError(run.stdout+run.stderr)
  aggregate=json.loads(subprocess.check_output([gn,"desc",str(out),"//:test","--format=json"],cwd=r,text=True))["//:test"]
  assert set(aggregate['libs']) == {'//'+selected+'/'+name+'-libraries' for name in names.values()}
  assert '//selected-headers/' in aggregate['include_dirs']
  for label in ("//third_party/dav1d:dav1d_headers", "//third_party/dav1d:dav1d_config", "//third_party/libaom:libaom_buildflags", "//third_party/opus:opus_config"):
   subprocess.run([gn,"desc",str(out),label],cwd=r,check=True,capture_output=True)
  for directory,name in names.items():
   label=f'//third_party/{directory}:emberbsd_{name}'
   info=json.loads(subprocess.check_output([gn,'desc',str(out),label,'--format=json'],cwd=r,text=True))[label]
   assert info['libs']==['//'+selected+'/'+name+'-libraries'] and info['inputs']==['//'+selected+'/'+name+'-inputs']
   assert info['ldflags']==['-Wl,-rpath='+ (str(r/'host') if role=='native' else '/usr/pkg/lib')]
 # Incomplete role selection must fail instead of falling back to another provider.
 out=r/'out-target'; args=out/'args.gn'; args.write_text(args.read_text().replace(
  f'emberbsd_vpx_target_libraries=["{r}/target/vpx-libraries"]', 'emberbsd_vpx_target_libraries=[]'))
 run=subprocess.run([gn,'gen',str(out),'--fail-on-unused-args'],cwd=r,text=True,capture_output=True)
 assert run.returncode and 'Selected codec provider is incomplete' in (run.stdout+run.stderr)
print('PASS: five codec wrappers select tracked role libraries, inputs and rpaths')
