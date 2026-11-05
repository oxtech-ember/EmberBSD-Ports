#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify the selected zlib/minizip role, inputs and runtime paths in GN."""
import argparse, json, subprocess, tempfile
from pathlib import Path
p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'gn', 'patch-tool'):
    p.add_argument('--'+name, type=Path, required=True)
a = p.parse_args(); base = a.source.resolve(strict=True)
patch = Path(__file__).resolve().parents[1]/'patches/gn-common-minizip-unicode.patch'
with tempfile.TemporaryDirectory() as tmp:
    r = Path(tmp).resolve()
    for name in ('build/linux/unbundle/zlib.gn', 'third_party/zlib/google/BUILD.gn',
                 'third_party/zlib/google/zip_reader.cc', 'third_party/zlib/google/zip_internal.cc'):
        q=r/name; q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes((base/name).read_bytes())
    subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=r,check=True)
    (r/'.gn').write_text('buildconfig = "//config.gn"\n')
    (r/'build/config/linux').mkdir(parents=True)
    (r/'build/config/linux/pkg_config.gni').write_text('')
    (r/'build/shim_headers.gni').write_text('template("shim_headers") { not_needed(invoker, "*") source_set(target_name) {} }\n')
    (r/'build_overrides').mkdir(); (r/'build_overrides/build.gni').write_text('build_with_chromium = true\n')
    (r/'BUILD.gn').write_text('group("test") { deps = [ "//third_party/zlib:zlib", "//third_party/zlib:minizip", "//third_party/zlib/google:zip" ] }\ntoolchain("tc") { tool("stamp") { command = "touch {{output}}" } tool("alink") { command = "touch {{output}}" outputs = [ "{{target_out_dir}}/{{target_output_name}}.a" ] } tool("cxx") { command = "touch {{output}}" outputs = [ "{{source_out_dir}}/{{source_name_part}}.o" ] } }\n')
    (r/'base').mkdir(); (r/'base/BUILD.gn').write_text('group("base") {}\ngroup("i18n") {}\n')
    (r/'third_party/zlib/BUILD.gn').write_text((r/'build/linux/unbundle/zlib.gn').read_text())
    for role in ('native','target'):
        selected = 'host' if role == 'native' else 'target'
        (r/'config.gn').write_text(f'set_default_toolchain("//:tc")\nemberbsd_pkg_config_role = "{role}"\nis_win = false\nis_ios = false\n')
        out=r/('out-'+role); out.mkdir()
        (out/'args.gn').write_text(''.join(f'emberbsd_{name}_{selected}_{kind} = [ "{r}/{selected}/{name}-{kind}" ]\n' for name in ('zlib','minizip') for kind in ('libraries','inputs') for selected in ('host','target')))
        for item_role in ('host','target'):
            (r/item_role).mkdir(exist_ok=True)
            for name in ('zlib','minizip'):
                for kind in ('libraries','inputs'): (r/item_role/(name+'-'+kind)).write_text('fixture')
        subprocess.run([str(a.gn),'gen',str(out),'--fail-on-unused-args'],cwd=r,check=True)
        for name in ('zlib','minizip'):
            data=json.loads(subprocess.check_output([str(a.gn),'desc',str(out),'//third_party/zlib:'+name,'--format=json'],cwd=r,text=True))
            target=data['//third_party/zlib:'+name]
            assert target['libs']==['//'+selected+'/'+name+'-libraries'] and target['inputs']==['//'+selected+'/'+name+'-inputs']
            expected=str(r/'host') if role=='native' else '/usr/pkg/lib'
            assert target['ldflags']==['-Wl,-rpath='+expected]
        result=subprocess.run([str(a.gn),'desc',str(out),'//third_party/zlib/google:zip','deps'],cwd=r,text=True,capture_output=True,check=True)
        assert '//third_party/zlib:zlib' in result.stdout and '//third_party/zlib:minizip' in result.stdout
print('PASS: GN selects role-specific owned libraries and inputs for zlib, minizip and Chromium ZIP')
