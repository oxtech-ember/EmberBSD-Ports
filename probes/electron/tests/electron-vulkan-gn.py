#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check selected Vulkan GN role inputs, platform configs and both callers."""
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('source','gn','patch-tool'): p.add_argument('--'+name, type=Path, required=True)
a=p.parse_args();source=a.source.resolve(strict=True);G=str(a.gn.resolve(strict=True))
patch=Path(__file__).resolve().parents[1]/'patches/gn-common-vulkan.patch'
with tempfile.TemporaryDirectory() as t:
 r=Path(t).resolve()
 def put(n,s):
  p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
 for n in ('build/linux/unbundle/replace_gn_files.py','third_party/angle/BUILD.gn','electron/BUILD.gn'):
  q=r/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/n,q)
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=r,check=True,capture_output=True)
 draft=r
 put('build/config/linux/pkg_config.gni','declare_args() { emberbsd_pkg_config_role="upstream" }\n')
 put('build_overrides/vulkan_headers.gni','')
 put('.gn','buildconfig="//config.gn"\n')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } tool("solink") { command="touch {{output}}" outputs=["{{root_out_dir}}/{{target_output_name}}.so"] } tool("link") { command="touch {{output}}" outputs=["{{root_out_dir}}/{{target_output_name}}"] } tool("cc") { command="touch {{output}}" outputs=["{{source_out_dir}}/{{source_name_part}}.o"] } }\ngroup("all") { deps=["//third_party/angle:libGLESv2","//electron:electron_app"] }\n')
 cond='''if (emberbsd_common_vulkan) {
      configs += [ "//build/config/emberbsd_vulkan:runtime_path" ]
    }'''
 assert cond in (draft/'third_party/angle/BUILD.gn').read_text() and cond in (draft/'electron/BUILD.gn').read_text()
 put('third_party/angle/BUILD.gn','import("//build/config/emberbsd_vulkan.gni")\nshared_library("libGLESv2") { sources=["dummy.c"] configs=[]\n'+cond+'\n data_deps=["//third_party/vulkan-loader/src:libvulkan"]\n public_deps=["//third_party/vulkan-headers/src:vulkan_headers"]\n}\n')
 put('electron/BUILD.gn','import("//build/config/emberbsd_vulkan.gni")\nexecutable("electron_app") { sources=["main.c"] configs=[]\n'+cond+'\n data_deps=["//third_party/vulkan-loader/src:libvulkan"]\n}\n')
 put('electron/main.c','int main(void) { return 0; }\n');put('third_party/angle/dummy.c','int fixture(void) { return 1; }\n');put('third_party/vulkan-loader/src/BUILD.gn',(draft/'build/linux/unbundle/vulkan-loader.gn').read_text());put('third_party/vulkan-headers/src/BUILD.gn',(draft/'build/linux/unbundle/vulkan-headers.gn').read_text())
 for role in ('host','target'):
  put('owned/'+role+'/libvulkan','owned');put('owned/'+role+'/metadata','owned');put('owned/'+role+'/headers/vulkan.h','owned')
 for role in ('target','explicit','native','upstream'):
  apple=role=='native';put('config.gn','set_default_toolchain("//:tc")\n'+''.join(k+'='+str(v).lower()+'\n' for k,v in {'is_win':False,'is_android':False,'is_fuchsia':False,'is_apple':apple,'is_mac':apple,'is_ios':False,'is_clang':True,'vulkan_use_x11':not apple,'vulkan_use_wayland':not apple}.items()))
  out=r/('out-'+role);out.mkdir();args=['emberbsd_common_vulkan=true','emberbsd_pkg_config_role="'+role+'"']
  for n in ('host','target'):
   root=r/'owned'/n; args += ['emberbsd_vulkan_'+n+'_library='+json.dumps(str(root/'libvulkan')),'emberbsd_vulkan_'+n+'_inputs='+json.dumps([str(root/'metadata')]),'emberbsd_vulkan_'+n+'_runtime_dir='+json.dumps(str(root) if n=='host' else '/usr/pkg/lib'),'emberbsd_vulkan_headers_'+n+'_include='+json.dumps(str(root/'headers')),'emberbsd_vulkan_headers_'+n+'_inputs='+json.dumps([str(root/'headers/vulkan.h')])]
  (out/'args.gn').write_text('\n'.join(args)+'\n');run=subprocess.run([G,'gen',str(out),'--fail-on-unused-args'],cwd=r,text=True,capture_output=True)
  if role=='upstream':assert run.returncode and 'unavailable for this toolchain' in run.stdout+run.stderr;continue
  assert not run.returncode,run.stdout+run.stderr;selected='host' if apple else 'target';lib='//third_party/vulkan-loader/src:libvulkan';hdr='//third_party/vulkan-headers/src:vulkan_headers'
  def desc(label):return json.loads(subprocess.check_output([G,'desc',str(out),label,'--format=json'],cwd=r,text=True))[label]
  li=desc(lib);assert len(li['inputs'])==2 and all('/'+selected+'/' in x for x in li['inputs']),li
  hd=desc(hdr);assert len(hd['inputs'])==1 and '/'+selected+'/' in hd['inputs'][0],hd
  for label in ('//third_party/angle:libGLESv2','//electron:electron_app'):
   data=desc(label);expected=('-Wl,-rpath,'+str(r/'owned/host')) if apple else '-Wl,-rpath=/usr/pkg/lib';assert expected in data['ldflags'],data
   runtime=subprocess.check_output([G,'desc',str(out),label,'runtime_deps'],cwd=r,text=True);assert 'owned/' not in runtime,runtime
  config=json.loads(subprocess.check_output([G,'desc',str(out),'//third_party/vulkan-headers/src:vulkan_headers_config','--format=json'],cwd=r,text=True))['//third_party/vulkan-headers/src:vulkan_headers_config']
  flags=config['defines']; assert ('VK_USE_PLATFORM_METAL_EXT' in flags)==apple and ('VK_USE_PLATFORM_XCB_KHR' in flags)==(not apple),flags
  original=(out/'args.gn').read_text()
  for kind in ('library','headers'):
   if kind=='library':
    broken=original.replace('emberbsd_vulkan_'+selected+'_library='+json.dumps(str(r/'owned'/selected/'libvulkan')),
                            'emberbsd_vulkan_'+selected+'_library=""')
   else:
    broken=original.replace('emberbsd_vulkan_headers_'+selected+'_inputs='+json.dumps([str(r/'owned'/selected/'headers/vulkan.h')]),
                            'emberbsd_vulkan_headers_'+selected+'_inputs=[]')
   assert broken != original
   (out/'args.gn').write_text(broken)
   failure=subprocess.run([G,'gen',str(out),'--fail-on-unused-args'],cwd=r,text=True,capture_output=True)
   assert failure.returncode and 'incomplete' in (failure.stdout+failure.stderr)
  (out/'args.gn').write_text(original)
 print('PASS native/target/explicit roles, owned inputs, both caller rpaths, platform defines, no bundled DSO; upstream rejected')
