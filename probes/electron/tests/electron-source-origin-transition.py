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
  prepared=[]
  def prepare(p):
   assert p in (candidate,stable) and (p/'identity').read_text()=='new' and cfg.read_text()=='old'
   prepared.append(p.name)
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
    with patch.object(t.shutil,'rmtree',side_effect=OSError('injected cleanup failure')):t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=old,verify_new=new,build_new=build,prepare_existing_new=prepare,commit_config=commit)
   else:t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=old,verify_new=new,build_new=build,prepare_existing_new=prepare,commit_config=commit)
  except (ValueError,OSError):
   if not (tamper or cleanup_failure):raise
   assert backup.exists() and marker.exists()
   if tamper:assert (backup/'foreign').read_text()=='do not remove'
  else:
   assert not (tamper or cleanup_failure) and not backup.exists() and not marker.exists();new(stable)
  assert prepared == ([] if tamper or state in ('initial','committed') else [candidate.name if state in ('before','missing') else stable.name])
  assert obj.read_bytes()==b'keep' and obj.stat().st_mtime_ns==before
for s in ('initial','before','missing','newstable','committed'):run(s)
run('newstable',tamper=True);run('newstable',cleanup_failure=True)
print('PASS: initial, three interrupted swaps, committed cleanup, foreign and cleanup failure; output mtime preserved')
with tempfile.TemporaryDirectory() as d:
 w=Path(d);view=w/'source-view';view.mkdir();(view/'identity').write_text('new');marker=w/'reconfigure-incomplete';marker.write_text('GN reconfiguration incomplete\nsource-origin-v1\n');cfg=w/'configuration.json';cfg.write_text('new')
 def verify_new(p):assert set(x.name for x in p.iterdir())=={'identity'} and (p/'identity').read_text()=='new'
 t.transition(w,saved_configuration=b'old',config_is_new=lambda:True,verify_old=lambda p:(_ for _ in ()).throw(AssertionError('no old backup')),verify_new=verify_new,build_new=lambda p:None,prepare_existing_new=lambda p:(_ for _ in ()).throw(AssertionError('cleanup refresh forbidden')),commit_config=lambda:None)
 assert not marker.exists()
print('PASS: committed new view recovery after backup deletion')
with tempfile.TemporaryDirectory() as d:
 w=Path(d);v=w/'source-view';v.mkdir();(v/'identity').write_text('old');out=w/'out';out.mkdir();obj=out/'obj';obj.write_text('keep');mtime=obj.stat().st_mtime_ns;cfg=w/'configuration.json';cfg.write_text('old')
 def old(p):assert (p/'identity').read_text()=='old'
 def new(p):assert (p/'identity').read_text()=='new'
 def bad(p):p.mkdir();(p/'foreign').write_text('preserve');raise ValueError('factory failed')
 def good(p):p.mkdir();(p/'identity').write_text('new')
 def commit():cfg.write_text('new')
 try:t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=old,verify_new=new,build_new=bad,prepare_existing_new=lambda p:None,commit_config=commit)
 except ValueError:pass
 else:raise AssertionError('factory failure ignored')
 retained=list(w.glob('.source-view-origin-factory-*'));assert len(retained)==1 and (retained[0]/'source-view/foreign').read_text()=='preserve'
 assert not (w/'.source-view-origin-candidate').exists() and not (w/'reconfigure-incomplete').exists()
 t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=old,verify_new=new,build_new=good,prepare_existing_new=lambda p:None,commit_config=commit)
 assert (retained[0]/'source-view/foreign').read_text()=='preserve' and obj.stat().st_mtime_ns==mtime
print('PASS: failed factory retains unknown data and retry succeeds')
for valid in (True,False):
 with tempfile.TemporaryDirectory() as d:
  w=Path(d);view=w/'source-view';view.mkdir();(view/'identity').write_text('old');candidate=w/'.source-view-origin-candidate';candidate.mkdir();(candidate/'identity').write_text('new' if valid else 'foreign');cfg=w/'configuration.json';cfg.write_text('old')
  def check(p,x):
   if (p/'identity').read_text()!=x:raise ValueError('foreign')
  try:t.transition(w,saved_configuration=b'old',config_is_new=lambda:cfg.read_text()=='new',verify_old=lambda p:check(p,'old'),verify_new=lambda p:check(p,'new'),build_new=lambda p:(_ for _ in ()).throw(AssertionError('must reuse candidate')),prepare_existing_new=lambda p:None,commit_config=lambda:cfg.write_text('new'))
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
 except ValueError as error:assert 'frozen provider selections' in str(error)
 else:raise AssertionError('verification accepted an activation flag')
 options.activate_common_providers=False;options.source_view_destination=root/'outside'
 try:controller.gn_source(options)
 except ValueError as error:assert 'sibling' in str(error)
 else:raise AssertionError('verification accepted a foreign view path')
print('PASS: selected-view verification rejects activation and foreign destination')

# Retired mirrors may lack new source entries, but every present entry is owned.
view_path=path.with_name('protobuf-source-view.py')
spec=importlib.util.spec_from_file_location('real_view',view_path);view=importlib.util.module_from_spec(spec);spec.loader.exec_module(view)
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary).resolve();source=root/'source';dest=root/'view';source.mkdir();dest.mkdir()
 (source/'keep').write_text('keep');(dest/'keep').write_text('keep')
 (source/'new').write_text('new');(source/'newdir').mkdir();(source/'newdir/file').write_text('new')
 try:view.mirror(source,dest,verify=True)
 except ValueError:pass
 else:raise AssertionError('normal build accepted incomplete mirror')
 view.mirror(source,dest,verify=True,retired=True)
 assert not (dest/'new').exists() and not (dest/'newdir').exists()
 (dest/'foreign').write_text('x')
 try:view.mirror(source,dest,verify=True,retired=True)
 except ValueError:pass
 else:raise AssertionError('retired mirror accepted foreign leaf')
 (dest/'foreign').unlink();(dest/'keep').write_text('changed')
 try:view.mirror(source,dest,verify=True,retired=True)
 except ValueError:pass
 else:raise AssertionError('retired mirror accepted changed bytes')
 (dest/'keep').unlink();(dest/'keep').symlink_to('foreign')
 try:view.mirror(source,dest,verify=True,retired=True)
 except ValueError:pass
 else:raise AssertionError('retired mirror accepted forged type')
 (dest/'keep').unlink();(dest/'keep').write_text('keep');(source/'link').symlink_to('target');(dest/'link').symlink_to('wrong')
 try:view.mirror(source,dest,verify=True,retired=True)
 except ValueError:pass
 else:raise AssertionError('retired mirror accepted changed symlink')
 try:view.mirror(source,dest,verify=True,retired=True,updates=[])
 except ValueError:pass
 else:raise AssertionError('retired mirror accepted mutation mode')
print('PASS: retired mirror subset and strict tamper/type/extra guards')

# Controller keeps retired verification selected and read-only and propagates failures.
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary).resolve();workspace=root/'workspace';(workspace/'src').mkdir(parents=True);work=root/'work';work.mkdir();dest=work/'source-view';dest.mkdir()
 options=Namespace(workspace=workspace,work=work,host_prefix=root,protobuf_source=root,phase='build',verify_selected_source_view=True)
 calls=[]
 class View:
  def verify(self,src,protobuf,destination,**kw):
   calls.append(kw)
   if kw.get('_retired'):raise ValueError('provider callback failed')
   return destination/'src'
 old_module=controller.local_module;controller.local_module=lambda name,filename:View()
 try:
  try:controller.gn_source(options,retired=True)
  except ValueError as error:assert 'provider callback' in str(error)
  else:raise AssertionError('retired verifier ignored callback failure')
  assert calls[-1]['_retired'] is True
  controller.gn_source(options);assert '_retired' not in calls[-1]
  options.verify_selected_source_view=False
  try:controller.gn_source(options,retired=True)
  except ValueError:pass
  else:raise AssertionError('nonselected retired verification accepted')
 finally:controller.local_module=old_module
print('PASS: retired routing and provider failure propagation')

# An aborted precommit leaves the old view incomplete for ordinary use.
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary).resolve();source=root/'source';source.mkdir();(source/'kept').write_text('same');(source/'added').write_text('new')
 work=root/'work';work.mkdir();old=work/'source-view';old.mkdir();(old/'kept').write_text('same');(work/'configuration.json').write_bytes(b'old')
 try:t.transition(work,saved_configuration=b'old',config_is_new=lambda:False,
                  verify_old=lambda p:view.mirror(source,p,verify=True,retired=True),
                  verify_new=lambda p:None,build_new=lambda p:(_ for _ in ()).throw(ValueError('factory failure')),
                  prepare_existing_new=lambda p:None,commit_config=lambda:None)
 except ValueError as error:assert 'factory failure' in str(error)
 else:raise AssertionError('factory failure accepted')
 try:view.mirror(source,old,verify=True)
 except ValueError:pass
 else:raise AssertionError('ordinary build accepted incomplete old view after failure')
print('PASS: precommit failure does not admit incomplete old view for build')

# Existing new view refresh happens only after old proof and honors provider checks.
for bad in (None, 'provider', 'foreign'):
 with tempfile.TemporaryDirectory() as temporary:
  root=Path(temporary).resolve();source=root/'source';source.mkdir();(source/'metadata').write_text('generated')
  work=root/'work';work.mkdir();stable=work/'source-view';(stable/'src').mkdir(parents=True);backup=work/'.source-view-origin-backup';backup.mkdir();(backup/'identity').write_text('old')
  config=work/'configuration.json';config.write_bytes(b'old');(work/'.source-view-origin-old-configuration.json').write_bytes(b'old');marker=work/'reconfigure-incomplete';marker.write_text(t.MARKER)
  if bad=='foreign':(stable/'src/foreign').write_text('preserve')
  def verify(source,protobuf,destination,*,_updates=None,_refresh=False,**kwargs):
   if bad=='provider':raise ValueError('provider proof failed')
   view.mirror(source,destination/'src',verify=True,updates=_updates)
   return destination/'src'
  saved_verify=view.verify;view.verify=verify;calls=[]
  def old(p):assert p==backup and (p/'identity').read_text()=='old';calls.append('old')
  def prepare(p):assert p==stable and calls and calls[-1]=='old';calls.append('prepare');view._refresh_leaves(source,None,p,{})
  def new(p):calls.append('new');verify(source,None,p)
  def commit():calls.append('commit');config.write_bytes(b'new')
  try:
   try:t.transition(work,saved_configuration=b'old',config_is_new=lambda:config.read_bytes()==b'new',verify_old=old,verify_new=new,build_new=lambda p:None,prepare_existing_new=prepare,commit_config=commit)
   except ValueError:
    if not bad:raise
    assert config.read_bytes()==b'old' and marker.exists() and backup.exists()
    if bad=='foreign':assert (stable/'src/foreign').read_text()=='preserve'
   else:
    assert bad is None and (stable/'src/metadata').read_text()=='generated' and calls[:4]==['old','prepare','new','commit']
  finally:view.verify=saved_verify
print('PASS: existing new view refresh honors old and provider proofs')

# Combined legacy recovery checks existing views before hooks, then refreshes new only.
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary).resolve();work=root/'work';work.mkdir();stable=work/'source-view';stable.mkdir();backup=work/'.source-view-origin-backup';backup.mkdir();factory=work/'.factory/source-view';events=[];source=root/'source';source.mkdir()
 def old(p,*,legacy_root=None):assert p==backup and not (source/'metadata').exists();events.append('old-legacy' if legacy_root else 'old-strict')
 def new(p,*,legacy_root=None):assert p==stable and not (source/'metadata').exists();events.append('new-legacy' if legacy_root else 'new-strict')
 def migrate(p,previous):events.append('migrate-old' if p==backup else 'migrate-new')
 def hooks():events.append('hooks');(source/'metadata').write_text('generated')
 controller.complete_ml_alias_migration('recovery',stable,backup,factory,old,new,migrate,hooks)
 assert events==['old-legacy','new-legacy','migrate-old','migrate-new','old-strict','new-strict','hooks']
 config=work/'configuration.json';config.write_bytes(b'old');(work/'.source-view-origin-old-configuration.json').write_bytes(b'old');(work/'reconfigure-incomplete').write_text(t.MARKER)
 def checked_old(p):assert p==backup;events.append('old-proof')
 def refresh(p):assert p==stable and (source/'metadata').read_text()=='generated';events.append('refresh')
 def checked_new(p):assert p==stable;events.append('new-proof')
 def commit():events.append('gn');config.write_bytes(b'new')
 t.transition(work,saved_configuration=b'old',config_is_new=lambda:config.read_bytes()==b'new',verify_old=checked_old,verify_new=checked_new,build_new=lambda p:None,prepare_existing_new=refresh,commit_config=commit)
 assert events[7:11]==['old-proof','refresh','new-proof','gn']
print('PASS: legacy recovery precedes hooks, new refresh and GN')

# Explicit migration accepts only its initial or guarded interrupted state.
with tempfile.TemporaryDirectory() as temporary:
 work=Path(temporary).resolve();stable=work/'source-view';stable.mkdir();config=work/'configuration.json';config.write_bytes(b'old');factory=work/'.source-view-origin-factory-proof'/'source-view'
 def mode(root,**kw):return controller.ml_alias_migration_mode(work,config,b'old',root,origin=True,cleanup_only=False,build_after=False,marker_text=t.MARKER,**kw)
 assert mode(stable)=='initial'
 try:mode(factory)
 except ValueError:pass
 else:raise AssertionError('initial foreign alias root accepted')
 (work/'.source-view-origin-backup').mkdir();(work/'.source-view-origin-old-configuration.json').write_bytes(b'old');(work/'reconfigure-incomplete').write_text(t.MARKER)
 assert mode(factory)=='recovery'
 try:mode(stable)
 except ValueError:pass
 else:raise AssertionError('recovery accepted wrong factory root')
 (work/'.source-view-origin-candidate').mkdir()
 try:mode(factory)
 except ValueError:pass
 else:raise AssertionError('unexpected candidate accepted')
print('PASS: explicit ML alias migration state and roots')

# Invalid alias migration CLI combinations fail before source/SDK preflight.
for previous,build_after in ((None,False),(Path('/old'),True)):
 opts=Namespace(migrate_ml_alias_root=Path('/selected'),previous_source=previous,build_after_reconfigure=build_after)
 try:controller.reconfigure(opts)
 except ValueError as error:assert 'requires separate source-origin' in str(error)
 else:raise AssertionError('invalid ML alias migration invocation accepted')
print('PASS: invalid ML migration invocation rejected before preflight')

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

# Only verified SPIRV recipe identities may move in the shared catalog.
import copy,json
names=('parallel/spirv-headers','parallel/spirv-tools','archivers/brotli')
def catalog():
 return {'version':1,'identities':{n:{'api':3,'package':n,'upstream':'f'*40,'effective_package_sha256':'a'*64} for n in names},'recipes':{n:{'distinfo':'d'*64,'patches':{'test':1}} for n in names}}
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
key='EMBERBSD_COMPRESSION_RECIPE_CATALOG'; before=catalog(); after=copy.deepcopy(before)
for n in names[:2]:after['identities'][n]['effective_package_sha256']='b'*64
old_catalog={key:encoded(before)}; new_catalog={key:encoded(after)}
controller.verify_source_origin_provider_invariants(old_catalog,new_catalog,verified_spirv=True)
def reject(value,proof=True):
 try:controller.verify_source_origin_provider_invariants(old_catalog,{key:value},verified_spirv=proof)
 except ValueError:pass
 else:raise AssertionError('invalid catalog transition accepted')
reject(encoded(after),False)
for mutate in ('foreign','recipe','identity','package','missing','extra','boolversion','floatapi','foreignfloat','recipetype','badsha'):
 bad=copy.deepcopy(after)
 if mutate=='foreign':bad['identities'][names[2]]['effective_package_sha256']='c'*64
 elif mutate=='recipe':bad['recipes'][names[0]]['distinfo']='e'*64
 elif mutate=='identity':bad['identities'][names[0]]['upstream']='e'*40
 elif mutate=='package':bad['identities'][names[0]]['package']=names[1]
 elif mutate=='missing':del bad['identities'][names[0]]
 elif mutate=='extra':bad['identities']['other']={}
 elif mutate=='boolversion':bad['version']=True
 elif mutate=='floatapi':bad['identities'][names[0]]['api']=3.0
 elif mutate=='foreignfloat':bad['identities'][names[2]]['api']=3.0
 elif mutate=='recipetype':bad['recipes'][names[0]]['patches']['test']=True
 elif mutate=='badsha':bad['identities'][names[0]]['effective_package_sha256']='z'*64
 reject(encoded(bad))
reject(encoded(after).replace('"version":1','"version":1,"version":1'))
bad_old=copy.deepcopy(before);bad_old['identities'][names[0]]['effective_package_sha256']='bad'
try:controller.verify_source_origin_provider_invariants({key:encoded(bad_old)},new_catalog,verified_spirv=True)
except ValueError:pass
else:raise AssertionError('invalid saved catalog hash accepted')
print('PASS: verified SPIRV catalog transition and negative cases')

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
