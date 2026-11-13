# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import importlib.util,os,tempfile
from pathlib import Path
from unittest.mock import patch
path=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/source-origin-transition.py'
spec=importlib.util.spec_from_file_location('source_origin_transition',path);t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

def run(state, tamper=False, cleanup_failure=False):
 with tempfile.TemporaryDirectory() as d:
  w=Path(d); out=w/'out';out.mkdir();obj=out/'obj';obj.write_bytes(b'keep'); before=obj.stat().st_mtime_ns
  stable=w/'source-view';candidate=w/'.source-view-origin-candidate';backup=w/'.source-view-origin-backup';marker=w/'reconfigure-incomplete';cfg=w/'configuration.json';cfg.write_text('old')
  def mk(p,kind):p.mkdir();(p/'identity').write_text(kind)
  def check(p,kind):
   if not t.real_directory(p) or set(x.name for x in p.iterdir()) != {'identity'} or (p/'identity').read_text()!=kind:raise ValueError('foreign view')
  def old(p):check(p,'old')
  def new(p):check(p,'new')
  def build(p):mk(p,'new')
  def commit():cfg.write_text('new')
  mk(stable,'old')
  if state!='initial':
   mk(candidate,'new');(w/'.source-view-origin-old-configuration.json').write_bytes(b'old');marker.write_text('GN reconfiguration incomplete\nsource-origin-v1\n')
   if state!='before':
    stable.rename(backup)
    if state!='missing':
     candidate.rename(stable)
     if state=='committed':cfg.write_text('new')
  if tamper:(backup/'foreign').write_text('do not remove')
  try:
   if cleanup_failure:
    with patch.object(t.shutil,'rmtree',side_effect=OSError('injected cleanup failure')):t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=old,verify_new=new,build_new=build,commit_config=commit)
   else:t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=old,verify_new=new,build_new=build,commit_config=commit)
  except (ValueError,OSError):
   if not (tamper or cleanup_failure):raise
   assert backup.exists() and marker.exists()
   if tamper:assert (backup/'foreign').read_text()=='do not remove'
  else:
   assert not (tamper or cleanup_failure) and not backup.exists() and not marker.exists();new(stable)
  assert obj.read_bytes()==b'keep' and obj.stat().st_mtime_ns==before
for s in ('initial','before','missing','newstable','committed'):run(s)
run('newstable',tamper=True);run('newstable',cleanup_failure=True)
print('PASS: initial, three interrupted swaps, committed cleanup, foreign and cleanup failure; output mtime preserved')
with tempfile.TemporaryDirectory() as d:
 w=Path(d);view=w/'source-view';view.mkdir();(view/'identity').write_text('new');marker=w/'reconfigure-incomplete';marker.write_text('GN reconfiguration incomplete\nsource-origin-v1\n');cfg=w/'configuration.json';cfg.write_text('new')
 def verify_new(p):assert set(x.name for x in p.iterdir())=={'identity'} and (p/'identity').read_text()=='new'
 t.transition(w,saved_configuration=b'old',config_is_new=lambda:True,verify_old=lambda p:(_ for _ in ()).throw(AssertionError('no old backup')),verify_new=verify_new,build_new=lambda p:None,commit_config=lambda:None)
 assert not marker.exists()
print('PASS: committed new view recovery after backup deletion')
with tempfile.TemporaryDirectory() as d:
 w=Path(d);v=w/'source-view';v.mkdir();(v/'identity').write_text('old');out=w/'out';out.mkdir();obj=out/'obj';obj.write_text('keep');mtime=obj.stat().st_mtime_ns;cfg=w/'configuration.json';cfg.write_text('old')
 def old(p):assert (p/'identity').read_text()=='old'
 def new(p):assert (p/'identity').read_text()=='new'
 def bad(p):p.mkdir();(p/'foreign').write_text('preserve');raise ValueError('factory failed')
 def good(p):p.mkdir();(p/'identity').write_text('new')
 def commit():cfg.write_text('new')
 try:t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=old,verify_new=new,build_new=bad,commit_config=commit)
 except ValueError:pass
 else:raise AssertionError('factory failure ignored')
 retained=list(w.glob('.source-view-origin-factory-*'));assert len(retained)==1 and (retained[0]/'source-view/foreign').read_text()=='preserve'
 assert not (w/'.source-view-origin-candidate').exists() and not (w/'reconfigure-incomplete').exists()
 t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=old,verify_new=new,build_new=good,commit_config=commit)
 assert (retained[0]/'source-view/foreign').read_text()=='preserve' and obj.stat().st_mtime_ns==mtime
print('PASS: failed factory retains unknown data and retry succeeds')
for valid in (True,False):
 with tempfile.TemporaryDirectory() as d:
  w=Path(d);view=w/'source-view';view.mkdir();(view/'identity').write_text('old');candidate=w/'.source-view-origin-candidate';candidate.mkdir();(candidate/'identity').write_text('new' if valid else 'foreign');cfg=w/'configuration.json';cfg.write_text('old')
  def check(p,x):
   if (p/'identity').read_text()!=x:raise ValueError('foreign')
  try:t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=lambda p:check(p,'old'),verify_new=lambda p:check(p,'new'),build_new=lambda p:(_ for _ in ()).throw(AssertionError('must reuse candidate')),commit_config=lambda:cfg.write_text('new'))
  except ValueError:
   assert not valid and candidate.exists() and (candidate/'identity').read_text()=='foreign'
  else:assert valid and not candidate.exists() and cfg.read_text()=='new'
print('PASS: pre-marker candidate verified before reuse; foreign retained')

# The internal verification mode must reject operations which can mutate a view.
from argparse import Namespace
controller_path=path.with_name('build-electron.py')
spec=importlib.util.spec_from_file_location('electron_controller',controller_path)
controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary); options=Namespace(workspace=root,work=root/'work',host_prefix=root,protobuf_source=root,phase='build',verify_selected_source_view=True,activate_common_providers=True)
 try:controller.gn_source(options)
 except ValueError as error:assert 'read-only' in str(error)
 else:raise AssertionError('verification accepted an activation flag')
 options.activate_common_providers=False;options.source_view_destination=root/'outside'
 try:controller.gn_source(options)
 except ValueError as error:assert 'sibling' in str(error)
 else:raise AssertionError('verification accepted a foreign view path')
print('PASS: selected-view verification rejects activation and foreign destination')

# Old source roots must come from the saved producer contract, not a caller guess.
saved={'source':'/old/workspace','arguments':{'emberbsd_node_source_identity':'/old/node/emberbsd-prepared-source.json','emberbsd_node_configure_inputs':['v8-source=/old/v8']}}
assert controller.saved_source_origin_inputs(saved)==(Path('/old/workspace'),Path('/old/node'),Path('/old/v8'))
saved['arguments']['emberbsd_node_configure_inputs'].append('v8-source=/foreign')
try:controller.saved_source_origin_inputs(saved)
except ValueError:pass
else:raise AssertionError('duplicate saved V8 root accepted')
print('PASS: saved source paths and duplicate rejection')

# Origin migration cannot silently select different unrelated providers.
old={'EMBERBSD_ML_RUY_SHA256':'one','EMBERBSD_ML_HEADER_EIGEN3_SHA256':'one','EMBERBSD_MEDIA_HEADER_LIBYUV_SHA256':'one','EMBERBSD_SQLITE_SELECTION':'{"id":1}','EMBERBSD_OTS_SELECTION':'{"id":1}','EMBERBSD_LEVELDB_SELECTION':'{"id":1}','EMBERBSD_SPIRV_SELECTION':'{"id":1}','EMBERBSD_COMPRESSION_RECIPE_CATALOG':'one','EMBERBSD_FFMPEG_TARGET_PKGCONFIG':'one','EMBERBSD_DEVTOOLS_PROVIDER_SHA256':'one','EMBERBSD_NODE_SOURCE_SHA256':'old','EMBERBSD_V8_SOURCE_SHA256':'old'}
new=dict(old,EMBERBSD_NODE_SOURCE_SHA256='new',EMBERBSD_V8_SOURCE_SHA256='new')
controller.verify_source_origin_provider_invariants(old,new)
for key in old.keys() - {'EMBERBSD_NODE_SOURCE_SHA256','EMBERBSD_V8_SOURCE_SHA256'}:
 changed=dict(new);changed[key]='different'
 try:controller.verify_source_origin_provider_invariants(old,changed)
 except ValueError as error:assert key in str(error)
 else:raise AssertionError('changed provider accepted: '+key)
print('PASS: unrelated provider identity/selection changes rejected')

# The saved source identity is the hash of the complete canonical record.
import hashlib,json
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary).resolve(); source=root/'source';source.mkdir();owner=root/'scripts/source-inputs/node/source.py';owner.parent.mkdir(parents=True);owner.write_text('# fixture')
 record={'identity':{'recipe':'old'},'tree_sha256':'a'*64};digest=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 class Native:
  def tool(self,name):assert name=='python';return '/selected/python'
 class Process:
  def capture(self,command,env):
   assert command[0]=='/selected/python' and command[-2:]==['--source',str(source)] and 'verify-payload' in command
   return Namespace(stdout=json.dumps(record).encode())
 options=Namespace(ports_source=root,sdk_source=root);saved={'environment':{'EMBERBSD_NODE_SOURCE_SHA256':digest}}
 controller.verify_saved_source_provider(options,{'process':Process()},Native(),{},saved,'NODE',source)
 saved['environment']['EMBERBSD_NODE_SOURCE_SHA256']='f'*64
 try:controller.verify_saved_source_provider(options,{'process':Process()},Native(),{},saved,'NODE',source)
 except ValueError as error:assert 'identity changed' in str(error)
 else:raise AssertionError('changed saved provider identity accepted')
print('PASS: old provider full-record identity checked')

# Header-only capability is explicit and retains all revision/path checks.
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary).resolve();host=root/'host';target=root/'target';host.mkdir();(target/'usr/pkg').mkdir(parents=True)
 o=Namespace(host_prefix=host,sysroot=target)
 def hdr(revision):
  out={}
  for role,prefix in (('host',host),('target',target/'usr/pkg')):
   stem='emberbsd_spirv_headers_'+role;pkg='spirv-headers-1.4.363.0'+revision
   out[stem+'_inputs']=[str(prefix/'include/spirv/unified1/spirv.h'),*[str(prefix/'pkgdb'/pkg/name) for name in ('+BUILD_INFO','+BUILD_VERSION','+CONTENTS')]]
  return out
 old,new=hdr(''),hdr('nb1')
 assert controller.provider_revision_args(o,'SPIRV',(('spirv_headers','spirv-headers',None),),old,new)=={'emberbsd_spirv_headers_host_inputs','emberbsd_spirv_headers_target_inputs'}
 changed=hdr('nb1');changed['emberbsd_spirv_headers_target_inputs'][0]+='.foreign'
 for providers,before,after in [((('spirv_headers','spirv-headers',None),),old,changed),((('foreign','foreign',None),),old,new),((('spirv_headers','spirv-headers','libraries'),),old,new)]:
  try:controller.provider_revision_args(o,'SPIRV',providers,before,after)
  except ValueError:pass
  else:raise AssertionError('invalid header-only revision accepted')
print('PASS: explicit SPIRV header-only revision and negative cases')

# A SPIR-V origin switch admits only proven prepared sources and package revisions.
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary).resolve();host=root/'host';target=root/'target';host.mkdir();(target/'usr/pkg').mkdir(parents=True)
 oldsel={'path':str(root/'old-spirv'),'tree_sha256':'a'*64,'receipt_sha256':'b'*64};newsel={'path':str(root/'new-spirv'),'tree_sha256':'a'*64,'receipt_sha256':'c'*64}
 selections={oldsel['path']:oldsel,newsel['path']:newsel}
 class FakeSpirv:
  def selection(self,view,sourceprep,path):return selections[path]
 def module(name,file):
  if file=='spirv-source-view.py':return FakeSpirv()
  if file=='protobuf-source-view.py':return object()
  raise AssertionError(file)
 options=Namespace(shared_spirv_tools=True,host_prefix=host,sysroot=target,spirv_selection=newsel,ml_sdk={'sourceprep':object()})
 keys=('EMBERBSD_SPIRV_TOOLS_SOURCE_SHA256','EMBERBSD_SPIRV_HEADERS_SOURCE_SHA256','EMBERBSD_SPIRV_LINK_SOURCE_SHA256','EMBERBSD_SPIRV_CORE_SOURCE_SHA256')
 oldenv={k:'a'*64 for k in keys};newenv={k:'b'*64 for k in keys}
 oldenv['EMBERBSD_SPIRV_SELECTION']=json.dumps(oldsel,sort_keys=True,separators=(',',':'));newenv['EMBERBSD_SPIRV_SELECTION']=json.dumps(newsel,sort_keys=True,separators=(',',':'))
 def args(revision,selection):
  out={'emberbsd_common_spirv_tools':True,'emberbsd_spirv_source_identity':selection['path']+'/emberbsd-prepared-source.json'}
  for role,prefix in (('host',host),('target',target/'usr/pkg')):
   for provider,base,version in (('spirv_tools','spirv-tools','2026.4'),('spirv_link','spirv-tools','2026.4'),('spirv_core','spirv-tools','2026.4'),('spirv_headers','spirv-headers','1.4.363.0')):
    stem='emberbsd_'+provider+'_'+role;rev=('nb4' if provider!='spirv_headers' else '') if not revision else ('nb5' if provider!='spirv_headers' else 'nb1')
    out[stem+'_inputs']=[str(prefix/'include'/provider),*[str(prefix/'pkgdb'/(base+'-'+version+rev)/name) for name in ('+BUILD_INFO','+BUILD_VERSION','+CONTENTS')]]
    if provider!='spirv_headers':out[stem+'_libraries']=[str(prefix/'lib'/provider)]
   out['emberbsd_spirv_tools_'+role+'_table']=str(prefix/'share/spirv-tools/generated/core_tables_header.inc')
  return out
 before,after=args(False,oldsel),args(True,newsel)
 with patch.object(controller,'local_module',side_effect=module):
  changed=controller.spirv_activation_args(options,oldenv,newenv,before,after,'emberbsd-prepared-source.json',origin=True)
  assert 'emberbsd_spirv_source_identity' in changed and 'emberbsd_spirv_headers_target_inputs' in changed
  selections[oldsel['path']]=dict(oldsel,tree_sha256='d'*64)
  try:controller.spirv_activation_args(options,oldenv,newenv,before,after,'emberbsd-prepared-source.json',origin=True)
  except ValueError:pass
  else:raise AssertionError('tampered old SPIRV payload accepted')
 print('PASS: SPIRV old/new payload proof and revision transition')
