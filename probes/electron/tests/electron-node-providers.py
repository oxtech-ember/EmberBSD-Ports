#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run real Chromium WebUI Rollup and TypeScript actions with shared providers."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','work','git','sdk-source','host-prefix','node-input-archive'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();root=args.work
    assert all(value.is_absolute() for value in vars(args).values())
    assert not root.exists() and not root.is_relative_to(args.source)
    root.mkdir(parents=True)
    sys.path.insert(0,str(args.sdk_source/'src'))
    from emberbsd_sdk.host_prefix import load_host_prefix
    from emberbsd_sdk.process import sanitized_environment
    native=load_host_prefix(args.host_prefix,required_roles=('python','node','gn','ninja','rollup','tsc','cp','touch'))
    assert Path(sys.executable).resolve()==Path(native.tool('python')).resolve()
    owner=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('node_providers',owner/'electron44/files/node-providers.py')
    providers=importlib.util.module_from_spec(spec);spec.loader.exec_module(providers)
    selected=providers.select(native)
    assert selected['arguments']['emberbsd_devtools_esbuild_module'] == str(args.host_prefix/'lib/node_modules/esbuild/lib/main.js')
    assert selected['arguments']['emberbsd_devtools_esbuild_binary'] == str(args.host_prefix/'bin/esbuild')
    assert selected['arguments']['emberbsd_devtools_esbuild_version']
    env=sanitized_environment();env.update(PATH=native.path,EMBERBSD_HOST_NODE=native.tool('node'),PYTHONDONTWRITEBYTECODE='1')
    env.update(selected['environment'])
    commands=[]
    def run(label,argv,*,cwd=root,environment=env,error=None):
        result=subprocess.run(list(map(str,argv)),cwd=cwd,env=environment,text=True,capture_output=True)
        output=result.stdout+result.stderr;(root/(label+'.log')).write_text(output)
        commands.append(dict(label=label,argv=list(map(str,argv)),status=result.returncode))
        assert (result.returncode==0 if error is None else result.returncode!=0 and error in output),label+': '+output
        return result.stdout
    tree=root/'source';tree.mkdir()
    names=['package.json','third_party/node/node.py','third_party/node/node_modules.py','third_party/node/node.gni',
           'third_party/node/BUILD.gn','third_party/node/check_version.py','third_party/node/check_version.js',
           'third_party/node/update_node_binaries','third_party/node/emberbsd_host_node_version',
           'third_party/node/node_modules.tar.gz.sha1','third_party/devtools-frontend/src/scripts/devtools_paths.py',
           'ui/webui/resources/tools/bundle_js.py','ui/webui/resources/tools/rollup_plugin.mjs']
    names += [str(p.relative_to(args.source)) for p in (args.source/'tools/typescript').iterdir()
              if p.is_file() and p.suffix in ('.py','.gni','.gn','.json')]
    before={}
    for name in names:
        data=(args.source/name).read_bytes();path=tree/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        before[name]=hashlib.sha256(data).hexdigest()
    patch=owner/'patches/gn-shared-node-providers.patch'
    run('patch-check',[args.git,'apply','--check',patch],cwd=tree)
    run('patch',[args.git,'apply',patch],cwd=tree)
    # Copy only pinned declaration source inputs, never the archive's toolchain
    # or old Rollup WASM binary. The full-source owner remains its DEPS pin.
    assert hashlib.sha256(args.node_input_archive.read_bytes()).hexdigest()=='a298af5fafd358179d6aec9a42f667902dbcdb03a42ee4a87a1bff83515e96b9'
    extracted=[]
    with tarfile.open(args.node_input_archive,'r:gz') as archive:
        for member in archive:
            name=member.name.removeprefix('./')
            if name.startswith('@types/trusted-types/') and member.isfile():
                target=tree/'third_party/node/node_modules'/name
                assert target.resolve().is_relative_to(tree)
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.extractfile(member).read());extracted.append(name)
    assert any(name.endswith('index.d.ts') for name in extracted),extracted
    for name in ('build/toolchain/rbe.gni','build/toolchain/siso.gni','ui/webui/webui_features.gni'):
        p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('')
    (tree/'.gn').write_text('buildconfig="//BUILDCONFIG.gn"\nscript_executable='+json.dumps(sys.executable)+'\n')
    (tree/'BUILDCONFIG.gn').write_text('''host_os="mac"
host_cpu="arm64"
use_remoteexec=false
use_typescript_go=false
is_ios=false
is_chromeos=false
TESTONLY_AND_VISIBILITY=["testonly","visibility"]
set_default_toolchain("//:tools")
''')
    (tree/'BUILD.gn').write_text('''group("all") { deps=["//tools/typescript/tests/provider:build_ts", "//fixture:bundle"] }
toolchain("tools") {
 tool("stamp") { command="touch {{output}}" }
 tool("copy") { command="cp -f {{source}} {{output}}" }
}
''')
    ts=tree/'tools/typescript/tests/provider';ts.mkdir(parents=True)
    (ts/'entry.ts').write_text('export const answer: number = 42;\n')
    (ts/'BUILD.gn').write_text('import("//tools/typescript/ts_library.gni")\nts_library("build_ts") { in_files=["entry.ts"] composite=true }\n')
    fixture=tree/'fixture';fixture.mkdir()
    (fixture/'entry.js').write_text('import { value } from "./value.js";\nexport const answer = value + 1;\n')
    (fixture/'value.js').write_text('export const value = 41;\n')
    (fixture/'BUILD.gn').write_text('''import("//third_party/node/node.gni")
node("bundle") {
 script="//ui/webui/resources/tools/bundle_js.py"
 inputs=["entry.js","value.js","//ui/webui/resources/tools/rollup_plugin.mjs"]
 outputs=["$target_gen_dir/entry.rollup.js","$target_gen_dir/entry.rollup.js.map","$target_gen_dir/fixture_requestlist.txt"]
 args=["--depfile",rebase_path("$target_gen_dir/bundle.d",root_build_dir),
       "--target_name","fixture","--host","fixture",
       "--input",rebase_path(".",root_build_dir),
       "--out_folder",rebase_path(target_gen_dir,root_build_dir),"--js_module_in_files","entry.js"]
 depfile="$target_gen_dir/bundle.d"
}
''')
    out=tree/'out';out.mkdir()
    values=selected['arguments']
    (out/'args.gn').write_text(''.join(key+'='+json.dumps(value)+'\n' for key,value in values.items()))
    run('gn',[native.tool('gn'),'gen',out],cwd=tree)
    inputs=json.loads(run('ts-inputs',[native.tool('gn'),'desc',out,'//tools/typescript/tests/provider:build_ts','inputs','--format=json'],cwd=tree))
    inputs=inputs['//tools/typescript/tests/provider:build_ts']['inputs']
    assert selected['environment']['EMBERBSD_HOST_TYPESCRIPT'] in inputs
    assert set(values['emberbsd_typescript_definitions'])<=set(inputs)
    run('ninja',[native.tool('ninja'),'-C',out,'-j','1'],cwd=tree)
    assert (out/'gen/tools/typescript/tests/provider/entry.js').is_file()
    assert (out/'gen/tools/typescript/tests/provider/entry.d.ts').is_file()
    bundle=out/'gen/fixture/entry.rollup.js'
    assert bundle.is_file() and 'value + 1' in bundle.read_text()
    assert 'value.js' in (out/'gen/fixture/bundle.d').read_text()
    run('bundle-execute',[native.tool('node'),'--input-type=module','-e',
        'const m=await import('+json.dumps(bundle.as_uri())+'); if(m.answer!==42) process.exit(2)'])
    assert any(path.endswith('/lib/tsc') for path in inputs)
    assert any(path.endswith('.node') for path in inputs)
    # Check the actual DevTools selector, and preserve its standalone default.
    selector = root/'select.py'
    selector.write_text('import sys\n'
        'sys.path.insert(0,'+repr(str(tree/'third_party/devtools-frontend/src/scripts'))+')\n'
        'import devtools_paths\nprint(devtools_paths.rollup_path())\n')
    assert run('devtools-selected',[sys.executable,selector]).strip()==env['EMBERBSD_HOST_ROLLUP']
    for label, value in (('empty',''),('relative','relative/rollup'),('missing',str(root/'absent'))):
        invalid=dict(env);invalid['EMBERBSD_HOST_ROLLUP']=value
        run('devtools-'+label,[sys.executable,selector],environment=invalid,error='absolute JavaScript entry file')
    legacy=dict(env);legacy.pop('EMBERBSD_HOST_ROLLUP')
    assert run('devtools-legacy',[sys.executable,selector],environment=legacy).strip().endswith('/node_modules/rollup/dist/bin/rollup')
    # Removing the standard declarations from declared inputs must not bypass
    # Chromium's existing dependency check after the compiler succeeds.
    original_args=(out/'args.gn').read_text()
    without=dict(values);without['emberbsd_typescript_definitions']=[]
    (out/'args.gn').write_text(''.join(key+'='+json.dumps(value)+'\n' for key,value in without.items()))
    run('missing-declarations-gn',[native.tool('gn'),'gen',out],cwd=tree)
    run('missing-declarations-ninja',[native.tool('ninja'),'-C',out,'-j','1'],cwd=tree,
        error='Undeclared dependencies to definition files')
    (out/'args.gn').write_text(original_args)
    run('restored-declarations-gn',[native.tool('gn'),'gen',out],cwd=tree)
    run('restored-declarations-ninja',[native.tool('ninja'),'-C',out,'-j','1'],cwd=tree)
    # The old entry would select absent bundled tools; no archive binary is used.
    clean=dict(env);clean.pop('EMBERBSD_HOST_ROLLUP');clean.pop('EMBERBSD_HOST_TYPESCRIPT')
    run('unselected-rollup',[sys.executable,tree/'third_party/node/node.py',
        tree/'third_party/node/node_modules/@rollup/wasm-node/dist/bin/rollup','--version'],environment=clean,error='Cannot find module')
    (root/'result.json').write_text(json.dumps(dict(scope='actual GN/Ninja WebUI bundler and TypeScript CLI with installed shared providers; no full Electron graph or target execution',commands=commands,declarations=extracted),indent=2)+'\n')
    assert before=={name:hashlib.sha256((args.source/name).read_bytes()).hexdigest() for name in names}
    print('PASS: real WebUI Rollup and TypeScript GN/Ninja actions with selected common providers')


if __name__=='__main__':main()
