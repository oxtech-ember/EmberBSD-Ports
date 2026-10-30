#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise selected Chromium trusted-types routing with the actual TS backend."""
import argparse,json,os,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--host-prefix',type=Path,required=True);a=p.parse_args();src=a.source.resolve();host=a.host_prefix.resolve();installed=host/'lib/node_modules';backends=list((installed/'@typescript').glob('typescript-*/lib/tsc'))
if len(backends)!=1: raise SystemExit('expected one selected TypeScript native backend')
tsc=backends[0]; std=tsc.parent; trusted=installed/'@types/trusted-types';version=json.loads((trusted/'package.json').read_text())['version']
with tempfile.TemporaryDirectory(prefix='trusted-types-test-') as tmp:
 root=Path(tmp).resolve();tool=root/'tools/typescript';tool.mkdir(parents=True)
 for path in (src/'tools/typescript').iterdir():
  if path.is_file() and path.suffix in ('.py','.json'):shutil.copy2(path,tool/path.name)
 ts=root/'third_party/typescript';ts.mkdir(parents=True);shutil.copy2(src/'third_party/typescript/typescript.py',ts/'typescript.py');f=root/'fixture';f.mkdir();(f/'package.json').write_text('{"type":"module"}\n');out=root/'out';gen=out/'gen/fixture';gen.mkdir(parents=True)
 modules=root/'common';(modules/'@types').mkdir(parents=True);shutil.copytree(trusted,modules/'@types/trusted-types'); (modules/'@types/unwanted').mkdir();(modules/'@types/unwanted/index.d.ts').write_text('declare const unwantedAmbient: number;')
 definitions=list(std.glob('*.d.ts'))+list((modules/'@types/trusted-types').rglob('*.d.ts')); env=dict(PATH=str(host/'bin'),EMBERBSD_HOST_NODE=str(host/'bin/node'),EMBERBSD_TYPESCRIPT_NATIVE_BINARY=str(tsc),PYTHONDONTWRITEBYTECODE='1')
 cmd=[str(host/'bin/python3.15'),'-B',str(tool/'ts_library.py'),'--root_gen_dir','..','--root_src_dir','../../..','--root_dir','../fixture','--gen_dir','gen/fixture','--out_dir','gen/fixture','--output_suffix','fixture','--in_files','entry.ts','--common-node-modules',str(modules),'--trusted-types-version',version,'--toolchain_definitions',*[os.path.relpath(x,gen) for x in definitions],'--tsconfig_base','../../../fixture/custom.json']
 def run(config,source,ok=True):
  (f/'custom.json').write_text(json.dumps({'compilerOptions':config}));(f/'entry.ts').write_text(source);r=subprocess.run(cmd,cwd=out,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  if (r.returncode==0)!=ok: raise AssertionError(r.stdout)
  return r.stdout
 source='export const useTrusted = (x: TrustedHTML): TrustedHTML => x;\n'
 run({'types':[]},source);c=json.loads((gen/'tsconfig_fixture.json').read_text());assert c['compilerOptions']['typeRoots'][0]==str(modules/'@types') and c['compilerOptions']['types']==['trusted-types']
 (root/'custom-types/trusted-types').mkdir(parents=True);(root/'custom-types/trusted-types/index.d.ts').write_text('type TrustedHTML = number;\n')
 run({'types':['trusted-types'],'typeRoots':['../custom-types']},source);files=subprocess.check_output([str(tsc),'--project',str(gen/'tsconfig_fixture.json'),'--listFilesOnly'],cwd=out,env=env,text=True);assert str(modules/'@types/trusted-types/index.d.ts') in files and str(root/'custom-types/trusted-types/index.d.ts') not in files
 run({},'export const x = 1;\n// @ts-expect-error common ambient must not leak\nexport const y = unwantedAmbient;\n');c=json.loads((gen/'tsconfig_fixture.json').read_text());assert 'typeRoots' not in c['compilerOptions']
 err=run({'typeRoots':['../third_party/node/node_modules/@types']},source,False);assert 'requires explicit types' in err
 print('TS common provider, competing roots, implicit ambient, bundled guard PASS')
