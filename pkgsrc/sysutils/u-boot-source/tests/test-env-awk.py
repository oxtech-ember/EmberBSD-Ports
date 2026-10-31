# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
import ast, os, subprocess, tempfile
from common import arguments
from types import SimpleNamespace
opts=arguments('Run upstream environment text checks with native nawk', compiler=False)
source=opts.source
nawk=(opts.host_prefix / 'bin/nawk').resolve(strict=True)
if not nawk.is_relative_to(opts.host_prefix):
 raise SystemExit('nawk resolves outside the selected host prefix')
path=source/'test/py/tests/test_env.py'
tree=ast.parse(path.read_text());test=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='test_env_text')
module=ast.Module(body=[test],type_ignores=[]);ast.fix_missing_locations(module)
class Utils:
 count=0
 @staticmethod
 def run_and_log(ubman,args):
  assert args[0]=='awk';Utils.count+=1
  return subprocess.run([str(nawk),*args[1:]],check=True,text=True,capture_output=True).stdout
scope={'os':os,'tempfile':tempfile,'utils':Utils}
exec(compile(module,str(path),'exec'),scope)
scope['test_env_text'](SimpleNamespace(config=SimpleNamespace(source_dir=str(source))))
print('upstream test_env_text cases passed:',Utils.count)
