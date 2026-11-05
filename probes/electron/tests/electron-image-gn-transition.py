#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check v62 bundled to v80 system transition changes both JPEG consumer flags."""
import argparse,json,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for n in ('source','gn','patch-tool'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args(); source=a.source.resolve(strict=True); patch=Path(__file__).resolve().parents[1]/'patches/gn-common-image.patch'
with tempfile.TemporaryDirectory() as td:
 r=Path(td).resolve()
 def put(path,data):
  f=r/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(data)
 for name in ('third_party/BUILD.gn','build/linux/unbundle/libwebp.gn'):
  f=r/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((source/name).read_bytes())
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=r,check=True,capture_output=True)
 put('.gn','buildconfig="//config.gn"\n')
 put('config.gn','set_default_toolchain("//:tc")\nemberbsd_pkg_config_role="target"\nuse_blink=true\n')
 put('build/config/linux/pkg_config.gni','template("pkg_config") { not_needed(invoker, "*") config(target_name) { include_dirs=["//selected-headers"] } }\n')
 put('build/buildflag_header.gni','template("buildflag_header") { not_needed(invoker,"*") source_set(target_name) {} }\n')
 put('build/config/features.gni','')
 put('build/config/freetype/freetype.gni','use_system_freetype=false\nenable_freetype=true\n')
 put('third_party/harfbuzz/harfbuzz.gni','use_system_harfbuzz=false\n')
 put('third_party/libjpeg.gni','declare_args() { use_system_libjpeg=false }\nuse_libjpeg_turbo=true\n')
 put('third_party/libjpeg_turbo/BUILD.gn','config("libjpeg_config") { include_dirs=[ "src" ] defines=[ "MANGLE_JPEG_NAMES" ] }\nsource_set("libjpeg") { public_configs=[ ":libjpeg_config" ] }\n')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } tool("cxx") { command="touch {{output}}" outputs=["{{source_out_dir}}/{{source_name_part}}.o"] } }\ngroup("test") { deps=[ "//consumer:jpeg", "//consumer:headers" ] }\n')
 put('consumer/BUILD.gn','source_set("jpeg") { sources=["jpeg.cc"] deps=["//third_party:jpeg"] }\nsource_set("headers") { sources=["headers.cc"] deps=["//third_party:jpeg_includes"] }\n')
 put('consumer/jpeg.cc','int jpeg_consumer;\n');put('consumer/headers.cc','int jpeg_headers;\n')
 for kind in ('libraries','inputs'): put('jpeg-'+kind,'fixture')
 states={}
 for state in ('old','new'):
  out=r/('out-'+state);out.mkdir()
  if state=='new':
   (out/'args.gn').write_text(f'emberbsd_common_image=true\nuse_system_libjpeg=true\nemberbsd_jpeg_target_libraries=["{r}/jpeg-libraries"]\nemberbsd_jpeg_target_inputs=["{r}/jpeg-inputs"]\n')
  subprocess.run([str(a.gn),'gen',str(out),'--fail-on-unused-args'],cwd=r,check=True,capture_output=True)
  for label in ('jpeg','headers'):
   data=json.loads(subprocess.check_output([str(a.gn),'desc',str(out),'//consumer:'+label,'--format=json'],cwd=r,text=True))['//consumer:'+label]
   states[state,label]=(set(data.get('defines',[])),set(data.get('include_dirs',[])))
 for label in ('jpeg','headers'):
  old,oldinc=states['old',label]; new,newinc=states['new',label]
  assert 'MANGLE_JPEG_NAMES' in old and 'USE_SYSTEM_LIBJPEG' in new
  assert 'MANGLE_JPEG_NAMES' not in new and oldinc != newinc
  assert '//selected-headers/' in newinc and '//third_party/libjpeg_turbo/src/' not in newinc
print('PASS: jpeg and jpeg_includes consumers change compile flags and bundled include paths')
