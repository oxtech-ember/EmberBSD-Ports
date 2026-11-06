#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check SPIRV-Tools role-specific GN labels and archive ordering."""
import argparse,json,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for n in ('source','gn','patch-tool'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();src=a.source.resolve(strict=True);gn=str(a.gn.resolve(strict=True));patch=Path(__file__).resolve().parents[1]/'patches/gn-common-spirv-tools.patch'
codecpatch=(patch.parent/'gn-common-codecs.patch').read_text().split('+++ b/build/config/emberbsd_codecs.gni\n',1)[1]
gni=''.join(line[1:] for line in codecpatch.splitlines(True)[1:] if line.startswith('+'))
with tempfile.TemporaryDirectory() as td:
 root=Path(td).resolve()
 def put(path,data):
  f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(data)
 f=root/'build/linux/unbundle/vulkan-SPIRV-Tools.gn';f.parent.mkdir(parents=True);f.write_bytes((src/'build/linux/unbundle/vulkan-SPIRV-Tools.gn').read_bytes())
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(patch)],cwd=root,check=True,capture_output=True)
 put('build/config/emberbsd_codecs.gni',gni)
 put('.gn','buildconfig="//config.gn"\n')
 put('build/config/linux/pkg_config.gni','template("pkg_config") { assert(invoker.ignore_libs) not_needed(invoker, "*") config(target_name) { include_dirs=["//selected-headers"] } }\n')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } }\nsource_set("test") { deps=["//third_party/spirv-tools:spvtools_opt"] }\nsource_set("combined") { deps=["//third_party/spirv-tools:spvtools", "//third_party/spirv-tools:spvtools_val", "//third_party/spirv-tools:spvtools_opt", "//third_party/spirv-tools:spvtools_link"] }\n')
 (root/'third_party/spirv-tools').mkdir(parents=True);shutil.copy2(f,root/'third_party/spirv-tools/BUILD.gn')
 for role in ('native','target'):
  put('config.gn',f'set_default_toolchain("//:tc")\nemberbsd_pkg_config_role="{role}"\nis_mac={'true' if role=='native' else 'false'}\n')
  out=root/('out-'+role);out.mkdir();selected='host' if role=='native' else 'target'
  identity=root/'source-receipt';identity.write_text('fixture')
  args='emberbsd_common_spirv_tools=true\n'+f'emberbsd_spirv_source_identity="{identity}"\n'
  for r in ('host','target'):
   for name,libs in [('spirv_core',['core']),('spirv_tools',['opt','core']),('spirv_link',['link','opt','core'])]:
    paths=[]
    for lib in libs:
     file=root/f'{r}-{lib}.a';file.write_text('fixture');paths.append('"'+str(file)+'"')
    if r=='target' and name in ('spirv_tools','spirv_link'):
     script=root/f'{r}-{name}-group.a';script.write_text('GROUP ( '+' '.join(paths)+' )');paths=['"'+str(script)+'"']
    inp=root/f'{r}-{name}-input';inp.write_text('fixture')
    args+=f'emberbsd_{name}_{r}_libraries=[{",".join(paths)}]\nemberbsd_{name}_{r}_inputs=["{inp}"]\n'
   hdr=root/f'{r}-headers';hdr.write_text('fixture');table=root/r/'core_tables_header.inc';table.parent.mkdir(exist_ok=True);table.write_text('fixture')
   args+=f'emberbsd_spirv_headers_{r}_inputs=["{hdr}"]\nemberbsd_spirv_tools_{r}_table="{table}"\n'
  (out/'args.gn').write_text(args)
  run=subprocess.run([gn,'gen',str(out),'--fail-on-unused-args'],cwd=root,text=True,capture_output=True)
  if run.returncode:raise RuntimeError(run.stdout+run.stderr)
  for label in ('selected_core','spvtools_opt','spvtools_link'):
   target='//third_party/spirv-tools:'+label
   info=json.loads(subprocess.check_output([gn,'desc',str(out),target,'--format=json'],cwd=root,text=True))[target]
   assert '//'+selected+'-core.a' in info['libs'],info['libs']
  label='//:combined';info=json.loads(subprocess.check_output([gn,'desc',str(out),label,'--format=json'],cwd=root,text=True))[label]
  assert '//selected-headers/' in info['include_dirs']
  if role=='native':
   expected={'//'+selected+'-'+x+'.a' for x in ('core','opt','link')}
  else:
   expected={'//target-core.a','//target-spirv_tools-group.a','//target-spirv_link-group.a'}
  assert set(info['libs'])==expected,info['libs']
  assert all('--whole-archive' not in x and '--start-group' not in x for x in info['ldflags'])
print('PASS: SPIRV core, opt and link labels use both selected roles and ordered archives')
