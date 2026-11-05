import importlib.util,sys,tempfile
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1])/'src'))
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
from emberbsd_sdk import inventory,sourceprep
from emberbsd_sdk.errors import SDKError
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
view=load('view',owner/'protobuf-source-view.py'); b=load('b',owner/'boringssl-source-view.py')
with tempfile.TemporaryDirectory() as t:
 r=Path(t).resolve(); source=r/'source'; origin=source/'third_party/boringssl';(origin/'src').mkdir(parents=True);(origin/'BUILD.gn').write_text('gn');(origin/'src/same').write_text('same');(origin/'src/different').write_text('old')
 provider=r/'provider';provider.mkdir();(provider/'same').write_text('same');(provider/'different').write_text('new')
 selected=r/'view/src/third_party';selected.mkdir(parents=True);(selected/'boringssl').symlink_to(origin,target_is_directory=True);keep=selected/'keep';keep.write_text('outside'); before=(keep.stat().st_ino,keep.stat().st_mtime_ns); same=(origin/'src/same').stat().st_mtime_ns
 real=b.projection.prepare_projection
 def fail(*args,**kwargs): raise ValueError('injected failure')
 b.projection.prepare_projection=fail
 try:
  try: b.activate(view,source,r/'view',provider,'a'*64,inventory,sourceprep,lambda:None)
  except ValueError as e: assert str(e)=='injected failure'
  else: raise AssertionError('failure not propagated')
 finally: b.projection.prepare_projection=real
 assert (selected/'boringssl').is_symlink()
 b.activate(view,source,r/'view',provider,'a'*64,inventory,sourceprep,lambda:None)
 assert (selected/'boringssl/src/same').stat().st_mtime_ns==same and (selected/'boringssl/src/different').read_text()=='new';assert (keep.stat().st_ino,keep.stat().st_mtime_ns)==before
 b.activate(view,source,r/'view',provider,'a'*64,inventory,sourceprep,lambda:None,old_digest='a'*64)
 # Simulate configure dying after the real projection was committed, before
 # the configuration receipt was saved. The controller must recognize only
 # the verified new digest before its other selection callbacks run.
 from types import SimpleNamespace
 from unittest.mock import patch
 controller=load('controller',owner/'build-electron.py')
 stable=(keep.stat().st_ino,keep.stat().st_mtime_ns)
 class WholeView:
  require=staticmethod(view.require)
  entries=staticmethod(view.entries)
  def verify(self,*args,**kwargs):
   assert 'boringssl' in kwargs['ml_names']
   kwargs['ml_verify']()
   return r/'view/src'
  def _refresh_leaves(self,*args): return self.verify(*args[:3],**args[3])
 fake_ml=SimpleNamespace(NAMES=('litert',),verify_view=lambda *args:None)
 fake_hdr=SimpleNamespace(NAMES=('eigen3',),verify_view=lambda *args:None)
 fake_media=SimpleNamespace(NAMES=('libyuv',),identity=lambda data,name:'m',verify_view=lambda *args:None)
 fake_comp=SimpleNamespace(NAMES=('brotli','zstd'),verify_view=lambda *args:None)
 modules={'electron_protobuf_source_view':WholeView(),'electron_boringssl_source_view':b,
          'electron_ml_source_view':fake_ml,'electron_header_source_view':fake_hdr,
          'electron_media_header_view':fake_media,'electron_compression_source_view':fake_comp}
 workspace=r/'workspace';workspace.mkdir();(workspace/'src').symlink_to(source, target_is_directory=True)
 options=SimpleNamespace(workspace=workspace,work=r,protobuf_source=r/'protobuf',host_prefix=r,
  ml_identities={'litert':'l'},old_ml_identities={'litert':'l'},ml_sources={},
  ml_sdk={'inventory':inventory,'sourceprep':sourceprep},ml_headers={'eigen3':{'identity':'h'}},
  old_header_identities={'eigen3':'h'},media_header_selections={},old_media_header_identities={'libyuv':'m'},
  compression_identity='c',old_compression_identity='c',boringssl_identity='a'*64,
  old_boringssl_identity=None,boringssl_selected=provider,phase='configure',retry_configure=True)
 (r/'view').rename(r/'source-view')
 try:
  with patch.object(controller,'local_module',side_effect=lambda name,path:modules[name]):
   options.boringssl_identity='b'*64
   try: controller.gn_source(options)
   except SDKError: pass
   else: raise AssertionError('unverified retry digest accepted')
   options.boringssl_identity='a'*64
   controller.gn_source(options)
 finally:
  (r/'source-view').rename(r/'view')
 assert (keep.stat().st_ino,keep.stat().st_mtime_ns)==stable
 marker=r/'.view.boringssl-components-migration';marker.write_text('foreign')
 try: b.activate(view,source,r/'view',provider,'a'*64,inventory,sourceprep,lambda:None,old_digest='a'*64)
 except ValueError: pass
 else: raise AssertionError('foreign marker accepted')
 assert marker.read_text()=='foreign'
 print('PASS: projection preserves mtimes, recovers interruption, rejects foreign marker')
