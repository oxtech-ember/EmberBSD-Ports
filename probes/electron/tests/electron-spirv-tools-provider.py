#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check codec provider ownership, versions, checksums and both roles."""
import hashlib, importlib.util, json, tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name,file):
 s=importlib.util.spec_from_file_location(name,owner/file); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=load('electron','build-electron.py'); image=load('image','image-provider.py'); codec=load('codec','codec-provider.py')
c.atomic_write=load('view','protobuf-source-view.py')._write_transaction_marker
assert image.package_at_least('spirv-tools-2026.4nb5', 'spirv-tools', (2026, 4, 0, 5))
assert not image.package_at_least('spirv-tools-2026.4nb4', 'spirv-tools', (2026, 4, 0, 5))
assert image.package_at_least('vulkan-loader-1.4.363.0', 'vulkan-loader', (1, 4, 363, 0, 0))
assert not image.package_at_least('vulkan-loader-1.4.362.99nb999', 'vulkan-loader', (1, 4, 363, 0, 0))
assert not image.package_at_least('vulkan-loader-1.4..363', 'vulkan-loader', (1, 4, 363, 0, 0))
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp).resolve(); host=root/'host'; target=root/'sysroot/usr/pkg'; view=root/'view'; dbs={'host':{},'target':{}}; inputs={}
 for role,prefix,suffix in (('host',host,'.a'),('target',target,'.a')):
  for name,(path,base,minimum,libraries,modules,headers) in (codec.SPIRV_TOOLS_PROVIDER | codec.SPIRV_HEADERS_PROVIDER).items():
   pkg=prefix/'pkgdb'/(base+('-2026.4nb5' if name=='spirv_tools' else '-1.4.363.0nb1'));pkg.mkdir(parents=True);dbs[role][path]=[pkg]
   entries=list(headers)+['lib/pkgconfig/'+m+'.pc' for m in modules]+['lib/'+lib+suffix for lib in libraries]
   if name=='spirv_tools':entries.append('lib/libSPIRV-Tools-link.a')
   contents=['@blddep spirv-headers-1.4.363.0nb1'] if name=='spirv_tools' else []
   for entry in entries:
    f=prefix/entry;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('owned');contents += [entry,'@comment MD5:'+hashlib.md5(b'owned',usedforsecurity=False).hexdigest()]
    if role=='host' and entry.endswith('.pc'):
     inputs[str(f)]={};v=view/entry;v.parent.mkdir(parents=True,exist_ok=True);v.write_text('selected')
   (pkg/'+CONTENTS').write_text('\n'.join(contents)+'\n')
   for n in ('+BUILD_INFO','+BUILD_VERSION'): (pkg/n).write_text('owned')
 meta=root/'metadata';meta.mkdir();(meta/'selection.json').write_text(json.dumps({'identity':{'inputs':inputs}}))
 o=SimpleNamespace(shared_spirv_tools=True,work=root,host_prefix=host,sysroot=root/'sysroot',host_buildlink_pkgsrc=root/'pkgsrc',_common_native_packages=dbs['host'],_common_target_packages=dbs['target'],_compression_catalog={'recipes':{x[0]:{} for x in (codec.SPIRV_TOOLS_PROVIDER | codec.SPIRV_HEADERS_PROVIDER).values()}})
 native=SimpleNamespace(host={'os':'Darwin'},tool=lambda n:'/selected/'+n)
 sdk={'process':SimpleNamespace(capture=lambda command,env:SimpleNamespace(stdout=('1.0\n'*(len(command)-command.index('--modversion')-1)).encode()))}
 env={'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(meta)}
 with patch.object(c,'validate_package_source') as verify:
  v=codec.select_spirv_tools(image,c,o,sdk,native,env,view);assert verify.call_count==8 and len(env['EMBERBSD_SPIRV_TOOLS_SOURCE_SHA256'])==64
  assert len(v['emberbsd_spirv_tools_host_libraries'])==2 and v['emberbsd_spirv_tools_target_libraries'][0].endswith('.a')
  assert [Path(x).name for x in v['emberbsd_spirv_tools_host_libraries']] == ['libSPIRV-Tools-opt.a', 'libSPIRV-Tools.a']
  script=Path(v['emberbsd_spirv_link_target_libraries'][0]);group=script.read_text()
  assert group.index('libSPIRV-Tools-link.a') < group.index('libSPIRV-Tools-opt.a') < group.index('libSPIRV-Tools.a')
  assert str(script) in v['emberbsd_spirv_link_target_inputs']
  old_mtime=script.stat().st_mtime_ns;codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  assert script.stat().st_mtime_ns==old_mtime
  persistent={name:Path(v['emberbsd_'+name+'_target_libraries'][0]) for name in ('spirv_tools','spirv_link')}
  before={name:(path.read_bytes(),path.stat().st_mtime_ns) for name,path in persistent.items()}
  with tempfile.TemporaryDirectory(dir=root,prefix='candidate-') as candidate:
   o.work=Path(candidate);o.native_binding_root=root
   candidate_values=codec.select_spirv_tools(image,c,o,sdk,native,env,view)
   assert all(Path(candidate_values['emberbsd_'+name+'_target_libraries'][0])==path for name,path in persistent.items())
   assert all(str(path) in candidate_values['emberbsd_'+name+'_target_inputs'] for name,path in persistent.items())
  assert all(path.is_file() and (path.read_bytes(),path.stat().st_mtime_ns)==before[name] for name,path in persistent.items())
  o.work=root
  del o.native_binding_root
  normal=codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  assert all(Path(normal['emberbsd_'+name+'_target_libraries'][0])==path and path.stat().st_mtime_ns==before[name][1] for name,path in persistent.items())
  definition=codec.SPIRV_TOOLS_PROVIDER['spirv_tools'];changed=definition[:3]+(tuple(reversed(definition[3])),)+definition[4:]
  with patch.dict(codec.SPIRV_TOOLS_PROVIDER,{'spirv_tools':changed}):
   altered=codec.select_spirv_tools(image,c,o,sdk,native,env,view)
   changed_path=Path(altered['emberbsd_spirv_tools_target_libraries'][0])
   assert changed_path!=persistent['spirv_tools'] and changed_path.is_file()
   assert all((path.read_bytes(),path.stat().st_mtime_ns)==before[name] for name,path in persistent.items())
  victim=persistent['spirv_tools'];victim.write_bytes(b'foreign')
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError:pass
  else:raise AssertionError('modified GROUP input accepted')
  assert victim.read_bytes()==b'foreign'
  victim.write_bytes(before['spirv_tools'][0])
  assert [Path(x).name for x in v['emberbsd_spirv_core_host_libraries']] == ['libSPIRV-Tools.a']
  contents=dbs['target']['parallel/spirv-tools'][0]/'+CONTENTS'; original=contents.read_text()
  contents.write_text(original.replace('@blddep spirv-headers-1.4.363.0nb1', '@blddep spirv-headers-1.4.363.0'))
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'different SPIRV-Headers' in str(error)
  else:raise AssertionError('different build headers accepted')
  contents.write_text(original)
  header=target/'include/spirv/unified1/spirv.hpp11';header.write_text('altered')
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'differs' in str(error)
  else:raise AssertionError('changed SPIRV-Headers accepted')
  header.write_text('owned')
  table=target/'share/spirv-tools/generated/core_tables_header.inc';table.write_text('different')
  old_hash=hashlib.md5(b'owned',usedforsecurity=False).hexdigest()
  new_hash=hashlib.md5(b'different',usedforsecurity=False).hexdigest()
  contents.write_text(original.replace('share/spirv-tools/generated/core_tables_header.inc\n@comment MD5:'+old_hash,
                                      'share/spirv-tools/generated/core_tables_header.inc\n@comment MD5:'+new_hash))
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'source tables differ' in str(error)
  else:raise AssertionError('mismatched generated tables accepted')
  table.write_text('owned');contents.write_text(original)
  f=target/'lib/libSPIRV-Tools.a';f.write_text('altered')
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'differs' in str(error)
  else:raise AssertionError('changed SPIRV-Tools common dependency accepted')
  f.write_text('owned')
  f=target/'lib/libSPIRV-Tools-opt.a';f.write_text('altered')
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'differs' in str(error)
  else:raise AssertionError('changed image library accepted')
  f.write_text('owned'); old=dbs['target']['parallel/spirv-tools'];dbs['target']['parallel/spirv-tools']=[]
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'selection missing' in str(error)
  else:raise AssertionError('missing target accepted')
  dbs['target']['parallel/spirv-tools']=old
  header=host/'include/spirv-tools/libspirv.h'; header.write_text('altered')
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'differs' in str(error)
  else:raise AssertionError('changed SPIRV-Tools header accepted')
  header.write_text('owned')
  pc=view/'lib/pkgconfig/SPIRV-Tools.pc';pc.unlink()
  try:codec.select_spirv_tools(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'not selected' in str(error)
  else:raise AssertionError('unselected native SPIRV-Tools pkg-config accepted')
print('PASS: SPIRV-Tools provider role ownership, checksums and missing dependency rejection')
