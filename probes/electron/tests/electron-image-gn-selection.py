#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse,json,subprocess,tempfile,shutil
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('source','gn','patch-tool'): p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); SRC=a.source.resolve(strict=True); GN=str(a.gn.resolve(strict=True))
PATCH=Path(__file__).resolve().parents[1]/'patches/gn-common-image.patch'
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp).resolve()
 for name in ('third_party/BUILD.gn','build/linux/unbundle/libwebp.gn'):
  dest=r/name; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes((SRC/name).read_bytes())
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(PATCH)],cwd=r,check=True,capture_output=True)
 def write(path,data):
  p=r/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 write('.gn','buildconfig = "//config.gn"\n')
 write('build/shim_headers.gni','template("shim_headers") { not_needed(invoker, "*") source_set(target_name) {} }\n')
 write('build/config/linux/pkg_config.gni','template("pkg_config") { not_needed(invoker, "*") config(target_name) {} }\n')
 write('build/buildflag_header.gni','template("buildflag_header") { not_needed(invoker, "*") source_set(target_name) {} }\n')
 write('build/config/features.gni','');write('build/config/ui.gni','');write('build/config/chrome_build.gni','');write('build/config/buildflags_paint_preview.gni','')
 write('build/config/freetype/freetype.gni','use_system_freetype = true\nenable_freetype = true\n')
 write('third_party/harfbuzz/harfbuzz.gni','use_system_harfbuzz = true\n')
 write('third_party/libjpeg.gni','use_system_libjpeg = true\nuse_libjpeg_turbo = true\n')
 write('BUILD.gn','toolchain("tc") { tool("stamp") { command = "touch {{output}}" } }\ngroup("test") { deps = [ "//skia:skia" ] }\n')
 write('skia/BUILD.gn','source_set("skia") { deps = [ "//third_party:jpeg", "//third_party/libwebp", "//third_party/libwebp:libwebp_sharpyuv" ] }\n')
 (r/'third_party/libwebp').mkdir(parents=True); shutil.copy2(r/'build/linux/unbundle/libwebp.gn',r/'third_party/libwebp/BUILD.gn')
 for role in ('native','target'):
  write('config.gn',f'''set_default_toolchain("//:tc")\nemberbsd_pkg_config_role="{role}"\nuse_blink=true\nbuild_with_chromium=false\nuse_gio=false\nis_castos=false\nis_win=false\nis_ios=false\nCHECK_INCLUDES_STRICT_PUBLIC_INCLUDES_PRIVATE=false\ntemplate("component") {{ source_set(target_name) {{ forward_variables_from(invoker,"*") }} }}\n''')
  out=r/('out-'+role);out.mkdir(); sel='host' if role=='native' else 'target'
  (out/'args.gn').write_text('emberbsd_common_image=true\n'+''.join(f'emberbsd_{n}_{selected_role}_{k}=["{r}/{selected_role}/{n}-{k}"]\n' for n in ('jpeg','webp') for k in ('libraries','inputs') for selected_role in ('host','target')))
  for selected_role in ('host','target'):
   (r/selected_role).mkdir(exist_ok=True)
   for n in ('jpeg','webp'):
    for k in ('libraries','inputs'): (r/selected_role/(n+'-'+k)).write_text('fixture')
  p=subprocess.run([GN,'gen',str(out),'--fail-on-unused-args'],cwd=r,text=True,capture_output=True); print(p.stdout,p.stderr);p.check_returncode()
  skia=json.loads(subprocess.check_output([GN,'desc',str(out),'//skia:skia','--format=json'],cwd=r,text=True))['//skia:skia']
  assert set(skia['libs']) == {'//'+sel+'/'+x+'-libraries' for x in ('jpeg','webp')}
  for label,name in (('//third_party:emberbsd_jpeg','jpeg'),('//third_party/libwebp:emberbsd_webp','webp')):
   info=json.loads(subprocess.check_output([GN,'desc',str(out),label,'--format=json'],cwd=r,text=True))[label]
   assert info['libs']==['//'+sel+'/'+name+'-libraries'] and info['inputs']==['//'+sel+'/'+name+'-inputs']; assert info['ldflags']==[('-Wl,-rpath,'+str(r/'host') if role=='native' else '-Wl,-rpath=/usr/pkg/lib')]
print('PASS image GN branches, tracked role inputs, transitive links and rpaths')
