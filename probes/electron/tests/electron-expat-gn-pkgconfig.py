#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the actual role-aware pkg-config template with both role inputs."""
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('source','gn','patch-tool','pkg-config'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();src=a.source.resolve(strict=True);gn=str(a.gn.resolve(strict=True));tests=Path(__file__).resolve().parents[1];patch=tests/'patches/gn-common-expat.patch'
codecpatch=(patch.parent/'gn-common-codecs.patch').read_text().split('+++ b/build/config/emberbsd_codecs.gni\n',1)[1]
gni=''.join(line[1:] for line in codecpatch.splitlines(True)[1:] if line.startswith('+'))
pc='prefix=@PREFIX@\nlibdir=${prefix}/lib\nincludedir=${prefix}/include\nName: expat\nDescription: Expat\nVersion: @VERSION@\nLibs: -L${libdir} -lexpat\nCflags: -I${includedir}\n'
with tempfile.TemporaryDirectory(prefix='electron-expat-pkgconfig-') as td:
 r=Path(td).resolve();host=r/'host';sysroot=r/'sysroot';target=sysroot/'usr/pkg'
 def write(path,data):
  f=r/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(data)
 for role,prefix in (('host',host),('target',target)):
  (prefix/'lib/pkgconfig').mkdir(parents=True);(prefix/'include').mkdir()
  (prefix/'lib/pkgconfig/expat.pc').write_text(pc.replace('@PREFIX@',str(host) if role=='host' else '/usr/pkg').replace('@VERSION@','2.10.0'))
  (prefix/'lib/libexpat.so').write_text('fixture')
 for n in ('build/linux/unbundle/replace_gn_files.py','build/config/linux/pkg_config.gni','build/config/linux/pkg-config.py'):
  f=r/n;f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/n,f)
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch.parent/'gn-common-pffft.patch')],cwd=r,check=True,capture_output=True)
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=r,check=True,capture_output=True)
 write('build/config/emberbsd_codecs.gni',gni)
 write('.gn','buildconfig="//config.gn"\n')
 write('build/shim_headers.gni','template("shim_headers") { not_needed(invoker, "*") source_set(target_name) {} }\n')
 write('build/config/compute_inputs_for_analyze.gni','compute_inputs_for_analyze=false\n')
 for n in ('build/config/gclient_args.gni','build/config/sysroot.gni','build/toolchain/rbe.gni'):write(n,'')
 write('BUILD.gn','toolchain("tc") { tool("stamp") { command="unused" } }\nsource_set("consumer") { deps=["//skia:consumer"] }\n')
 write('skia/BUILD.gn','source_set("consumer") { deps=["//third_party/expat:expat"] }\n')
 (r/'third_party/expat').mkdir(parents=True);shutil.copy2(r/'build/linux/unbundle/expat.gn',r/'third_party/expat/BUILD.gn')
 for role in ('native','target'):
  native=role=='native';provider=host if native else target; selected='host' if native else 'target'
  values={'emberbsd_pkg_config_role':role,'emberbsd_native_pkg_config_prefix':str(host),'emberbsd_native_pkg_config_buildlink':False,'emberbsd_target_sysroot':str(sysroot),'current_os':'mac' if native else 'netbsd','current_cpu':'arm64' if native else 'x64','sysroot':'' if native else str(sysroot),'target_sysroot':'' if native else str(sysroot),'use_sysroot':False,'use_remoteexec':False,'build_with_chromium':False}
  write('config.gn','set_default_toolchain("//:tc")\nhost_toolchain="//:tc"\n'+''.join(k+'='+json.dumps(v)+'\n' for k,v in values.items()))
  out=r/('out-'+role);out.mkdir();args=['emberbsd_common_expat=true','pkg_config='+json.dumps(str(a.pkg_config)),'host_pkg_config='+json.dumps(str(a.pkg_config))]
  for name,prefix in (('host',host),('target',target)):
   for kind in ('libraries','inputs'):args.append('emberbsd_expat_'+name+'_'+kind+'='+json.dumps([str(prefix/'lib/libexpat.so')]))
  (out/'args.gn').write_text('\n'.join(args)+'\n')
  run=subprocess.run([gn,'gen',str(out),'--fail-on-unused-args','--script-executable='+sys.executable],cwd=r,text=True,capture_output=True)
  if run.returncode:raise RuntimeError(run.stdout+run.stderr)
  info=json.loads(subprocess.check_output([gn,'desc',str(out),'//skia:consumer','--format=json','--script-executable='+sys.executable],cwd=r,text=True))['//skia:consumer']
  assert info['libs']==['//'+str((provider/'lib/libexpat.so').relative_to(r))],info
  assert len(info['cflags_cc'])==1 and str(provider/'include') in info['cflags_cc'][0],info
  assert info['ldflags']==[('-Wl,-rpath,'+str(provider/'lib') if native else '-Wl,-rpath=/usr/pkg/lib')],info
print('PASS: actual pkg-config template selects role headers and only the role EXPAT DSO')
