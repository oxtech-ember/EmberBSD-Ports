#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the FFmpeg wrapper's target and native GN selection."""
import argparse, json, tempfile, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','gn','patch-tool'): p.add_argument('--'+name, type=Path, required=True)
a=p.parse_args(); base=a.source.resolve(strict=True); gn=str(a.gn.resolve(strict=True))
patch=Path(__file__).resolve().parents[1]/'patches/gn-external-ffmpeg.patch'
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp).resolve(); paths=('third_party/ffmpeg/ffmpeg_options.gni','electron/BUILD.gn','build/config/linux/pkg-config.py','build/linux/unbundle/ffmpeg.gn')
 for name in paths:
  p=r/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((base/name).read_bytes())
 subprocess.run([str(a.patch_tool.resolve(strict=True)),'-p1','-i',str(patch)],cwd=r,check=True,capture_output=True)
 (r/'.gn').write_text('buildconfig = "//config.gn"\n'); (r/'config.gn').write_text('set_default_toolchain("//:tc")\nemberbsd_pkg_config_role = "target"\n')
 (r/'build/config/linux/pkg_config.gni').write_text('template("pkg_config") { not_needed(invoker, "*") config(target_name) {} }\n'); (r/'build/shim_headers.gni').write_text('template("shim_headers") { not_needed(invoker, "*") source_set(target_name) {} }\n'); (r/'build/buildflag_header.gni').write_text('template("buildflag_header") { not_needed(invoker, "*") source_set(target_name) {} }\n')
 (r/'provider.so').write_text('fixture');(r/'header.h').write_text('fixture'); (r/'args.txt').write_text('')
 (r/'BUILD.gn').write_text('''toolchain("tc") { tool("stamp") { command = "touch {{output}}" } }\n''')
 with (r/'build/linux/unbundle/ffmpeg.gn').open('a') as f: pass
 (r/'BUILD.gn').write_text('''toolchain("tc") { tool("stamp") { command = "touch {{output}}" } }\ngroup("test") { deps = [ "//third_party/ffmpeg:ffmpeg" ] }\n''')
 (r/'third_party/ffmpeg/BUILD.gn').write_text((r/'build/linux/unbundle/ffmpeg.gn').read_text()); out=r/'out'; out.mkdir(); (out/'args.gn').write_text(f'emberbsd_ffmpeg_target_libraries = [ "{r}/provider.so" ]\nemberbsd_ffmpeg_target_inputs = [ "{r}/header.h" ]\n')
 for role in ('target','explicit','native'):
  (r/'config.gn').write_text(f'set_default_toolchain("//:tc")\nemberbsd_pkg_config_role = "{role}"\n')
  out=r/('out-'+role); out.mkdir()
  (out/'args.gn').write_text(''.join(f'emberbsd_ffmpeg_{item_role}_libraries = [ "{r}/{item_role}/provider.so" ]\nemberbsd_ffmpeg_{item_role}_inputs = [ "{r}/{item_role}/header.h" ]\n' for item_role in ('host','target')))
  subprocess.run([gn,'gen',str(out)],cwd=r,check=True,capture_output=True)
  data=json.loads(subprocess.check_output([gn,'desc',str(out),'//third_party/ffmpeg:ffmpeg','--format=json'],cwd=r,text=True))
  selected=data['//third_party/ffmpeg:ffmpeg']
  chosen='host' if role=='native' else 'target'
  assert selected['libs']==['//'+chosen+'/provider.so'] and selected['inputs']==['//'+chosen+'/header.h']
  expected = '/usr/pkg/lib/ffmpeg9' if role != 'native' else str(r/'host')
  assert selected.get('ldflags',[]) == [('-Wl,-rpath,' if role=='native' else '-Wl,-rpath=')+expected]
print('PASS: GN selects tracked role-specific FFmpeg libraries and target runtime path')
