import argparse, hashlib, importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
parser=argparse.ArgumentParser();parser.add_argument('--sdk-source',type=Path,required=True);args=parser.parse_args()
sys.argv=[sys.argv[0]];sys.path.insert(0,str(args.sdk_source.resolve()/'src'))
from emberbsd_sdk import paths
from emberbsd_sdk.errors import SDKError
spec = importlib.util.spec_from_file_location('sqlite_view_draft', Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/sqlite-source-view.py')
viewmod = importlib.util.module_from_spec(spec); spec.loader.exec_module(viewmod)
class Controller:
 @staticmethod
 def require(value, message):
  if not value: raise ValueError(message)
class StableRead(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base=Path(self.temp.name).resolve(); source=self.base/'source';(source/'test').mkdir(parents=True)
  files={name:hashlib.sha256(name.encode()).hexdigest() for name in viewmod.FILES}
  raw=json.dumps({'format':'emberbsd-chromium-sqlite','version':1,'identity':{'source':str(source)},'files':files}).encode()
  self.root=self.base/('amalgamation-'+hashlib.sha256(raw).hexdigest());self.root.mkdir();(self.root/'receipt.json').write_bytes(raw)
  for name in viewmod.FILES:
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(name.encode())
 def test_atime_only_does_not_change_identity(self):
  p=self.root/'receipt.json';before=p.stat(); old=(before.st_atime_ns,before.st_mtime_ns); os.utime(p,ns=(1_000_000_000,old[1]));initial=p.stat();viewmod.selection(Controller,self.root);after=p.stat();self.assertEqual(paths.stable_identity(initial),paths.stable_identity(after))
 def test_mutations_refused(self):
  target=self.root/'receipt.json'; original=paths.open_regular
  for mode in ('bytes','inode','mtime','ctime'):
   with self.subTest(mode=mode):
    saved=target.read_bytes();done=[False]
    class Reader:
     def __init__(self, f):self.f=f
     def __enter__(self):return self
     def __exit__(self,*a):self.f.close()
     def fileno(self):return self.f.fileno()
     def read(self):
      data=self.f.read()
      if not done[0]:
       done[0]=True
       if mode=='bytes': target.write_bytes(b'X'+saved[1:])
       elif mode=='inode':
        q=target.with_suffix('.replacement');q.write_bytes(saved);os.replace(q,target)
       elif mode=='mtime':os.utime(target,ns=(target.stat().st_atime_ns,target.stat().st_mtime_ns+1_000_000_000))
       else:
        before=target.stat(); old_mode=before.st_mode & 0o777
        os.chmod(target,old_mode ^ 0o100); os.chmod(target,old_mode)
        after=target.stat(); assert after.st_mode == before.st_mode and after.st_ctime_ns != before.st_ctime_ns
        assert (after.st_ino,after.st_size,after.st_mtime_ns) == (before.st_ino,before.st_size,before.st_mtime_ns)
      return data
    def opened(path):
     f,b=original(path);return (Reader(f),b) if path==target else (f,b)
    with patch.object(paths,'open_regular',side_effect=opened):
     with self.assertRaisesRegex((SDKError,ValueError), 'changed during'):viewmod.selection(Controller,self.root)
    target.write_bytes(saved)
if __name__=='__main__':unittest.main()
