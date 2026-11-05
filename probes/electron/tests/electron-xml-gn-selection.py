#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify XML/XSLT system wrapper link inputs and propagated configurations."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

p=argparse.ArgumentParser(description=__doc__)
for name in ('source', 'gn', 'patch-tool'): p.add_argument('--'+name, type=Path, required=True)
a=p.parse_args(); base=a.source.resolve(strict=True); gn=str(a.gn.resolve(strict=True))
patch=Path(__file__).resolve().parents[1]/'patches/gn-external-xml.patch'
with tempfile.TemporaryDirectory(prefix='electron-xml-gn-') as tmp:
    root=Path(tmp).resolve()
    for name in ('libxml','libxslt'):
        path=Path('build/linux/unbundle')/(name+'.gn'); dest=root/path
        dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes((base/path).read_bytes())
    subprocess.run([str(a.patch_tool.resolve(strict=True)),'-p1','-i',str(patch)],cwd=root,check=True,capture_output=True)
    (root/'.gn').write_text('buildconfig = "//config.gn"\n')
    (root/'build/config/linux').mkdir(parents=True)
    (root/'build/config/linux/pkg_config.gni').write_text('template("pkg_config") { not_needed(invoker, "*") config(target_name) {} }\n')
    (root/'BUILD.gn').write_text('''toolchain("tc") { tool("stamp") { command = "touch {{output}}" } tool("alink") { command = "touch {{output}}" outputs = [ "{{target_out_dir}}/{{target_output_name}}.a" ] } tool("cxx") { command = "touch {{output}}" outputs = [ "{{source_out_dir}}/{{target_output_name}}.o" ] } }
group("test") { deps = [ "//third_party/libxml:libxml", "//third_party/libxslt:libxslt", "//third_party/libxml:xml_writer" ] }
''')
    for name in ('libxml','libxslt'):
        dest=root/'third_party'/name; dest.mkdir(parents=True)
        (dest/'BUILD.gn').write_text((root/'build/linux/unbundle'/(name+'.gn')).read_text())
    for role in ('target','native'):
        (root/'config.gn').write_text(f'set_default_toolchain("//:tc")\nemberbsd_pkg_config_role = "{role}"\n')
        output=root/('out-'+role); output.mkdir(); argrole='host' if role=='native' else 'target'
        (output/'args.gn').write_text(''.join(f'emberbsd_{key}_{argrole}_library = "{root}/{key}.so"\nemberbsd_{key}_{argrole}_inputs = [ "{root}/{key}.h" ]\n' for key in ('xml','xslt')))
        subprocess.run([gn,'gen',str(output)],cwd=root,check=True,capture_output=True)
        for name,key in (('libxml','xml'),('libxslt','xslt'),('libxml_utils','xml'),('xml_writer','xml')):
            owner='libxslt' if name=='libxslt' else 'libxml'
            data=json.loads(subprocess.check_output([gn,'desc',str(output),f'//third_party/{owner}:{name}','--format=json'],cwd=root,text=True))
            value=next(iter(data.values()))
            assert value['libs']==[f'//{key}.so']
            if name != 'xml_writer': assert value['inputs']==[f'//{key}.h']
            expected='/usr/pkg/lib' if role=='target' else str(root)
            assert value['ldflags']==['-Wl,-rpath='+expected]
print('PASS: GN XML/XSLT system link ownership and host/target paths')
