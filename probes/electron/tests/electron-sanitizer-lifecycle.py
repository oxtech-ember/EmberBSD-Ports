#!/usr/bin/env python3
"""Check diagnostic selection and new-work guards before producer mutation."""
import argparse, fcntl, importlib.util, json, tempfile, types
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--owner',type=Path,required=True);a=p.parse_args()
spec=importlib.util.spec_from_file_location('electron',a.owner/'build-electron.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from types import SimpleNamespace
gn={'is_official_build':True};m.apply_sanitizer_gn_args(gn,False);assert gn=={'is_official_build':True}
m.apply_sanitizer_gn_args(gn,True)
assert gn['is_official_build'] is False and gn['is_asan'] is True and gn['is_ubsan'] is True
assert 'use_allocator_shim' not in gn and 'use_partition_alloc_as_malloc' not in gn
assert 'is_ubsan_vptr' not in gn
opts=SimpleNamespace(sanitizer_package=Path('/package'),sanitizer_package_sha256='a'*64,sanitizer_resource=Path('/resource'),sanitizer_pkgsrc_export=Path('/export'),sanitizer_export_patch=Path('/patch'),compiler_family='clang',target='amd64',phase='build',build_test=False,build_after_reconfigure=False)
sdk={'targets':SimpleNamespace(target_definition=lambda target:{})}
def refused(fn):
 try:fn()
 except ValueError:return
 raise AssertionError('unsafe transition accepted')
refused(lambda:m.target_inputs(opts,sdk,None,{},Path('/work')))
saved={'environment':{'EMBERBSD_DIAGNOSTIC_SANITIZER':json.dumps(m.sanitizer_identity(opts),sort_keys=True)}}
m.require_sanitizer_continuation(saved,opts)
omit=SimpleNamespace(sanitizer_package=None,sanitizer_package_sha256=None,sanitizer_resource=None,sanitizer_pkgsrc_export=None,sanitizer_export_patch=None)
refused(lambda:m.require_sanitizer_continuation(saved,omit))
refused(lambda:m.require_sanitizer_continuation({'environment':{}},opts))
with tempfile.TemporaryDirectory() as td:
 opts.work=Path(td);opts.test_target=m.SERIAL_TEST_LABEL;opts.test_fonts_source=Path('/fonts');opts.resume_configure=True
 refused(lambda:m.initial_configuration_selection(opts))
 marker=opts.work/'pending-initial-selection.json'
 marker.write_text(json.dumps({'test_target':m.SERIAL_TEST_LABEL,'sanitizer':m.sanitizer_identity(opts),'test_fonts_source':'/fonts'}))
 assert m.initial_configuration_selection(opts)['test_target']==m.SERIAL_TEST_LABEL
 marker.write_text(json.dumps({'test_target':m.SERIAL_TEST_LABEL,'sanitizer':{'bad':True},'test_fonts_source':'/fonts'}))
 refused(lambda:m.initial_configuration_selection(opts))
 opts.sanitizer_package=None;opts.sanitizer_package_sha256=None;opts.sanitizer_resource=None
 opts.sanitizer_pkgsrc_export=None;opts.sanitizer_export_patch=None;opts.test_target=None;opts.test_fonts_source=None
 marker.unlink();assert m.initial_configuration_selection(opts)=={'test_target':None,'sanitizer':None,'test_fonts_source':None}
with tempfile.TemporaryDirectory() as td:
 opts.sanitizer_pkgsrc_export=Path(td)
 lock=Path(td)/'.pkgsrc-update.lock';lock.touch()
 with lock.open('r') as handle:
  fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:
   with m.sanitizer_export_guard(opts):pass
  except BlockingIOError:pass
  else:raise AssertionError('concurrent export update accepted')
 with m.sanitizer_export_guard(opts):pass
 (Path(td)/'.pkgsrc-update-incomplete').touch()
 refused(lambda: m.sanitizer_export_guard(opts).__enter__())
with tempfile.TemporaryDirectory() as td:
 recipe=Path(td);(recipe/'patches').mkdir();(recipe/'patches/patch-one').write_text('patch');(recipe/'distinfo').write_text('dist')
 expected=m.recipe_source_metadata(recipe)
 metadata='lang/compiler-rt/distinfo: '+expected['distinfo']+'\nlang/compiler-rt/patches/patch-one: '+expected['patches']['patch-one']+'\n'
 m.validate_package_source_data(metadata,expected,recipe,distinfo=True,package_path='lang/compiler-rt')
 refused(lambda:m.validate_package_source_data(metadata.replace(expected['patches']['patch-one'],'0'*64),expected,recipe,distinfo=True,package_path='lang/compiler-rt'))
opts.phase='reconfigure';opts.build_after_reconfigure=True
refused(lambda:m.target_inputs(opts,sdk,None,{},Path('/work')))
print('PASS: production build, omitted options and existing work rejected')

# The actual configure path must pass the focused pattern to GN and persist it.
from unittest.mock import patch
from contextlib import ExitStack, contextmanager
with tempfile.TemporaryDirectory() as td:
 root=Path(td); commands=[]; written=[]
 options=SimpleNamespace(work=root/'work',workspace=root,ports_source=root,git=root/'git',
                         sdk_source=root,host_prefix=root,target='amd64',test_target=m.SERIAL_TEST_LABEL,test_fonts_source=root/'fonts',
                         resume_configure=False,retry_configure=False,
                         sanitizer_package=None,sanitizer_package_sha256=None,sanitizer_resource=None,
                         sanitizer_pkgsrc_export=None,sanitizer_export_patch=None)
 native=SimpleNamespace(tool=lambda name:'/selected/'+name)
 active=[];validations=[]
 @contextmanager
 def linked(*args):
  active.append(True)
  try:yield
  finally:active.pop()
 def run_logged(cmd,*args,**kw):
  assert active and kw['env']['PYTHON_CPU_COUNT']=='1';commands.append(cmd)
 fonts=SimpleNamespace(validate=lambda *args:(validations.append(True) or root/'fonts'),recover=lambda *args:None,linked=linked)
 sdk={'process':SimpleNamespace(run_logged=run_logged)}
 def atomic(path,data):
  path.write_text(json.dumps(data));written.append((path,data))
 source=SimpleNamespace(atomic_json=atomic)
 with ExitStack() as stack:
  for name in ('require_common_v8','require_common_node','require_common_perfetto','require_common_dependencies',
               'verify_source','require_electron_static_assets','prepare_build_inputs','write_devtools_identity',
               'write_protoc_selection','write_v8_metagen_selection'):
   stack.enter_context(patch.object(m,name,lambda *args,**kw:None))
  stack.enter_context(patch.object(m,'load_sdk',lambda root:sdk))
  stack.enter_context(patch.object(m,'producer_inputs',lambda options,sdk:(native,{},{})))
  stack.enter_context(patch.object(m,'gn_source',lambda options:root))
  stack.enter_context(patch.object(m,'local_module',lambda name,path: fonts if name=='electron_test_fonts' else source))
  options.protoc_selection=None
  m.configure(options)
  def fail_gn(*args, **kwargs):
   assert active
   raise RuntimeError('test GN failure')
  options.work=root/'failed-work';sdk['process'].run_logged=fail_gn
  try:m.configure(options)
  except RuntimeError:pass
  else:raise AssertionError('GN failure swallowed')
  assert not active and (options.work/'pending-initial-selection.json').is_file()
  assert len(validations)==4
  options.work=root/'work'
 assert '--root-pattern='+m.SERIAL_TEST_LABEL in commands[0]
 assert written[-1][1]['test_target']==m.SERIAL_TEST_LABEL and len(validations)==4 and not active
 marker=options.work/'pending-initial-selection.json'
 assert not marker.exists()
 marker.write_text(json.dumps({'test_target':m.SERIAL_TEST_LABEL,'sanitizer':None,'test_fonts_source':str(options.test_fonts_source)}))
 options.resume_configure=True
 assert m.initial_configuration_selection(options)['test_target']==m.SERIAL_TEST_LABEL
 options.test_target=None
 refused(lambda:m.initial_configuration_selection(options))
print('PASS: actual configure selects/persists focused root and guards resume')
