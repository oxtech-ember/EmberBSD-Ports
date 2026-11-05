#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise codec wrappers with the actual role-aware pkg-config template."""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('source','gn','patch-tool','host-prefix','sysroot'): p.add_argument('--'+n,type=Path,required=True)
p.add_argument('--role',choices=('native','target'),required=True)
a=p.parse_args(); src=a.source.resolve(strict=True); prefix=a.host_prefix.resolve(strict=True)
patch=Path(__file__).resolve().parents[1]/'patches/gn-common-codecs.patch'
names={'dav1d':'dav1d','libaom':'aom','libvpx':'vpx','opus':'opus','flac':'flac'}
libs={'dav1d':'libdav1d','aom':'libaom','vpx':'libvpx','opus':'libopus','flac':'libFLAC'}
with tempfile.TemporaryDirectory(prefix='electron-codec-pkgconfig-') as td:
 r=Path(td)
 def write(name,data):
  path=r/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
 for n in [*(f'build/linux/unbundle/{x}.gn' for x in names),'media/base/BUILD.gn','media/base/libaom_thread_wrapper.cc','media/base/libvpx_thread_wrapper.cc','build/config/linux/pkg_config.gni','build/config/linux/pkg-config.py']:
  d=r/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/n,d)
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=r,check=True,capture_output=True)
 write('.gn','buildconfig="//config.gn"\n')
 write('build/shim_headers.gni','template("shim_headers") { not_needed(invoker, "*") config("${target_name}_config") {} source_set(target_name) { all_dependent_configs=[":${target_name}_config"] } }\n')
 write('build/buildflag_header.gni','template("buildflag_header") { not_needed(invoker, "*") source_set(target_name) {} }\n')
 write('third_party/libaom/options.gni','enable_libaom=true\n')
 write('build/config/compute_inputs_for_analyze.gni','compute_inputs_for_analyze=false\n')
 for n in ('build/config/gclient_args.gni','build/config/sysroot.gni','build/toolchain/rbe.gni'):write(n,'')
 write('BUILD.gn','toolchain("tc") { tool("stamp") { command="unused" } }\nsource_set("consumer") { deps=['+','.join('"//third_party/'+n+':'+n+'"' for n in names)+'] }\n')
 for n in names:
  d=r/'third_party'/n/'BUILD.gn';d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r/'build/linux/unbundle'/f'{n}.gn',d)
 native=a.role=='native'; provider=prefix if native else a.sysroot/'usr/pkg'; selected='host' if native else 'target'
 values={'emberbsd_pkg_config_role':a.role,'emberbsd_native_pkg_config_prefix':str(prefix),'emberbsd_native_pkg_config_buildlink':False,'emberbsd_target_sysroot':str(a.sysroot),'current_os':'mac' if native else 'netbsd','current_cpu':'arm64' if native else 'x64','sysroot':'' if native else str(a.sysroot),'target_sysroot':'' if native else str(a.sysroot),'use_sysroot':False,'use_remoteexec':False,'build_with_chromium':False}
 write('config.gn','set_default_toolchain("//:tc")\nhost_toolchain="//:tc"\n'+''.join(k+'='+json.dumps(v)+'\n' for k,v in values.items()))
 out=r/'out';out.mkdir();args=['emberbsd_common_codecs=true','pkg_config='+json.dumps(str(prefix/'bin/pkg-config')),'host_pkg_config='+json.dumps(str(prefix/'bin/pkg-config'))]
 for role_name, role_prefix, suffix in (('host',prefix,'.dylib'),('target',a.sysroot/'usr/pkg','.so')):
  for name,lib in libs.items():
   file=(role_prefix/'lib'/(lib+suffix)).resolve(strict=True)
   for kind in ('libraries','inputs'): args.append(f'emberbsd_{name}_{role_name}_{kind}='+json.dumps([str(file)]))
 (out/'args.gn').write_text('\n'.join(args)+'\n')
 run=subprocess.run([str(a.gn),'gen',str(out),'--fail-on-unused-args','--script-executable='+sys.executable],cwd=r,text=True,capture_output=True)
 if run.returncode:raise RuntimeError(run.stdout+run.stderr)
 info=json.loads(subprocess.check_output([str(a.gn),'desc',str(out),'//:consumer','--format=json','--script-executable='+sys.executable],cwd=r,text=True))['//:consumer']
 expected={str((provider/'lib'/(lib+('.dylib' if native else '.so'))).resolve(strict=True)) for lib in libs.values()}
 assert set(info['libs']) == expected,info
 for directory,name in names.items():
  label=f'//third_party/{directory}:emberbsd_{name}'
  selected_info=json.loads(subprocess.check_output([str(a.gn),'desc',str(out),label,'--format=json','--script-executable='+sys.executable],cwd=r,text=True))[label]
  assert selected_info['inputs'] == [str((provider/'lib'/(libs[name]+('.dylib' if native else '.so'))).resolve(strict=True))],selected_info
 assert len(info['cflags_cc']) == 5 and all(str(provider/'include') in x for x in info['cflags_cc']),info
 assert all(x == ('-Wl,-rpath,'+str(provider/'lib') if native else '-Wl,-rpath=/usr/pkg/lib') for x in info['ldflags']),info
print('PASS: actual pkg-config template, '+a.role+' codec paths and owned library selection')
