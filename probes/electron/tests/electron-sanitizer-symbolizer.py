import argparse,hashlib,importlib.util,json,shutil,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
parser=argparse.ArgumentParser();parser.add_argument('--sdk-source',type=Path,required=True);parser.add_argument('--symbolizer',type=Path,required=True);parser.add_argument('--readelf',type=Path,required=True);parser.add_argument('--owner',type=Path,default=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py');parser.add_argument('--llvm-version',required=True);args=parser.parse_args()
sdkroot=args.sdk_source.resolve();sys.path.insert(0,str(sdkroot/'src'))
from emberbsd_sdk import paths,targets,process
p=args.owner;spec=importlib.util.spec_from_file_location('e',p);e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
sdk={'paths':paths,'targets':targets,'process':process};real=args.symbolizer.resolve();readelf=str(args.readelf.absolute())
native=SimpleNamespace(tool=lambda name:readelf);env={'PATH':str(args.readelf.resolve().parent),'LC_ALL':'C'}
with tempfile.TemporaryDirectory() as d:
 root=Path(d).resolve();pre=root/'usr/pkg';tool=pre/'bin/llvm-symbolizer';tool.parent.mkdir(parents=True);shutil.copy2(real,tool);pkg=pre/('pkgdb/llvm-devel-'+args.llvm_version+'nb7');pkg.mkdir(parents=True);(pkg/'+BUILD_INFO').write_text('PKGPATH=lang/llvm-devel\n')
 def metadata():
  md5=hashlib.md5(tool.read_bytes(),usedforsecurity=False).hexdigest();(pkg/'+CONTENTS').write_text('@name '+pkg.name+'\nbin/llvm-symbolizer\n@comment MD5:'+md5+'\n')
 def reject():
  try:e.diagnostic_target_symbolizer(options,sdk,native,env)
  except (ValueError,OSError):return
  except Exception as x:
   if type(x).__name__=='SDKError':return
   raise
  raise AssertionError('invalid target tool accepted')
 options=SimpleNamespace(sysroot=root,target='amd64',sdk_source=sdkroot,_common_target_packages={'lang/llvm-devel':[pkg]},_sanitizer_llvm_version=args.llvm_version);metadata();t,h=e.diagnostic_target_symbolizer(options,sdk,native,env);assert t==str(tool) and h==hashlib.sha256(real.read_bytes()).hexdigest()
 (pkg/'+BUILD_INFO').write_text('PKGPATH=foreign/llvm-devel\n');reject();(pkg/'+BUILD_INFO').write_text('PKGPATH=lang/llvm-devel\n')
 raw=tool.read_bytes();tool.write_bytes(raw+b'x');reject();tool.write_bytes(raw)
 b=bytearray(raw);b[18:20]=(183).to_bytes(2,'little');tool.write_bytes(b);metadata();reject();tool.write_bytes(raw)
 assert b'NetBSD\0' in raw;tool.write_bytes(raw.replace(b'NetBSD\0',b'NotBSD\0'));metadata();reject();tool.write_bytes(raw);metadata();tool.chmod(0o644);reject();tool.chmod(0o755);tool.unlink();reject()
key='EMBERBSD_TARGET_SYMBOLIZER_SHA256';name='emberbsd_target_llvm_symbolizer';env={key:'a'*64};values={name:'/target/llvm-symbolizer'}
assert e.symbolizer_reconfigure_args({},env,{},values)==({key},{name});assert e.symbolizer_reconfigure_args(env,env,values,values)==(set(),set())
try:e.symbolizer_reconfigure_args({key:'b'*64},env,values,values)
except ValueError:pass
else:raise AssertionError('changed hash accepted')
try:e.symbolizer_reconfigure_args(env,env,values,{name:'/other/llvm-symbolizer'})
except ValueError:pass
else:raise AssertionError('changed path accepted')
print('PASS target symbolizer ownership, checksum, ABI, missing file, and reconfigure identity')
