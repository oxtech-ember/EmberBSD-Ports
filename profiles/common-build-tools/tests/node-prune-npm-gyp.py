#!/usr/bin/env python3
import argparse,importlib.util,json,os,shutil,tarfile,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--helper',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--work-dir',type=Path,required=True);a=p.parse_args()
spec=importlib.util.spec_from_file_location('prune',a.helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='node-prune-test-',dir=a.work_dir) as tmp:
 root=Path(tmp)/'source';root.mkdir();(root/'node.gyp').write_text('{}')
 pkg=root/'deps/npm/node_modules/node-gyp';(pkg/'lib').mkdir(parents=True);(pkg/'package.json').write_text(json.dumps({'name':'node-gyp'}));(pkg/'lib/configure.js').write_bytes(a.frontend.read_bytes())
 def create():
  g=pkg/'gyp';(g/'pylib/gyp').mkdir(parents=True);(g/'gyp_main.py').write_text('x');(g/'pylib/gyp/__init__.py').write_text('x');return g
 def reject(path):
  try:m.prune(path,archive)
  except ValueError:return
  raise AssertionError('invalid source accepted')
 g=create();archive=Path(tmp)/'source.tar'
 with tarfile.open(archive,'w') as tar:tar.add(g,arcname='source/deps/npm/node_modules/node-gyp/gyp')
 (g/'foreign').write_text('x');reject(root);(g/'foreign').unlink()
 (g/'gyp_main.py').write_text('changed');reject(root);(g/'gyp_main.py').write_text('x')
 m.prune(root,archive);assert not g.exists();m.prune(root,archive)
 os.symlink(Path(tmp),g);reject(root);g.unlink()
 g=create();(g/'pylib/gyp/__init__.py').unlink();(g/'pylib/gyp').rmdir();os.symlink(Path(tmp),g/'pylib/gyp');reject(root);(g/'pylib/gyp').unlink();shutil.rmtree(g)
 link=Path(tmp)/'link';os.symlink(root,link);reject(link)
 foreign=Path(tmp)/'foreign';foreign.mkdir();reject(foreign)
 (pkg/'lib/configure.js').write_text('old bundled frontend');reject(root)
 print('archive-identical prune + replay PASS; altered, extra, symlink and foreign root rejected')
