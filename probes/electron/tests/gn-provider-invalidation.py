#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise selected-provider commands with real GN/Ninja and Node."""
import argparse
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser()
for name in ('source','host-prefix','git'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();host=a.host_prefix;source=a.source
patch=Path(__file__).resolve().parents[1]/'patches/gn-node-provider-commands.patch'
assert all(x.is_absolute() for x in (source,host,a.git))

def run(argv, *, cwd, env):
    result=subprocess.run(list(map(str,argv)),cwd=cwd,env=env,capture_output=True,text=True)
    assert result.returncode==0,(argv,result.stdout,result.stderr)
    return result.stdout

with tempfile.TemporaryDirectory(prefix='gn-provider-tracking-') as tmp:
    root=Path(tmp);tree=root/'src';tree.mkdir()
    paths=['third_party/node/node.gni','third_party/node/node.py','third_party/node/node_modules.py',
           'third_party/devtools-frontend/src/scripts/build/typescript/typescript.gni',
           'third_party/devtools-frontend/src/scripts/build/ninja/node.gni',
           'third_party/devtools-frontend/src/scripts/build/typescript/ts_library.py',
           'third_party/devtools-frontend/src/inspector_overlay/BUILD.gn']
    for name in paths:
        dest=tree/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((source/name).read_bytes())
    base_env=dict(PATH=str(host/'bin'),LC_ALL='C',HOME=os.environ.get('HOME','/'))
    run([a.git,'apply','--check',patch],cwd=tree,env=base_env);run([a.git,'apply',patch],cwd=tree,env=base_env)
    for name in ('build/toolchain/rbe.gni','build/toolchain/siso.gni'):
        dest=tree/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('')
    (tree/'.gn').write_text('buildconfig="//BUILDCONFIG.gn"\n')
    (tree/'BUILDCONFIG.gn').write_text('host_os="mac"\nhost_cpu="arm64"\nuse_remoteexec=false\nbuild_with_chromium=true\nis_official_build=true\ndevtools_bundle=false\nTESTONLY_AND_VISIBILITY=["testonly","visibility"]\nset_default_toolchain("//:tools")\n')
    (tree/'BUILD.gn').write_text('group("all") { deps=["//fixture:test","//fixture:devtools_test","//fixture:devtools_ts","//fixture:js"] }\ntoolchain("tools") {\n tool("stamp") { command="touch {{output}}" }\n}\n')
    varsfile=tree/'third_party/devtools-frontend/src/scripts/build/ninja/vars.gni';varsfile.parent.mkdir(parents=True,exist_ok=True);varsfile.write_text('devtools_location_prepend="//third_party/devtools-frontend/src/"\n')
    tsbuild=tree/'tools/typescript';tsbuild.mkdir(parents=True);(tsbuild/'BUILD.gn').write_text('group("copy_package_json") {}\n')
    (tree/'package.json').write_text('{}'); (tree/'third_party/node/node_modules.tar.gz.sha1').write_text('fixture')
    (tree/'third_party/node/BUILD.gn').write_text('group("check_version") {}\n')
    fixture=tree/'fixture';fixture.mkdir()
    (fixture/'BUILD.gn').write_text('import("//third_party/node/node.gni")\nnode("test") {\n script="action.py"\n inputs=[]\n outputs=["$target_gen_dir/result"]\n args=[rebase_path(outputs[0],root_build_dir)]\n}\nimport("//third_party/devtools-frontend/src/scripts/build/typescript/typescript.gni")\ndevtools_provider_action("devtools_test") {\n script="action.py"\n inputs=[]\n outputs=["$target_gen_dir/devtools-result"]\n args=[rebase_path(outputs[0],root_build_dir)]\n}\nts_library("devtools_ts") { sources=["mini.ts"] }\n')
    jsdir=tree/'third_party/devtools-frontend/src/scripts';jsdir.mkdir(parents=True,exist_ok=True)
    (jsdir/'test.js').write_text('require("fs").writeFileSync(process.argv[2], process.env.EMBERBSD_HOST_NODE + "/" + process.env.EMBERBSD_HOST_TYPESCRIPT + "/" + process.env.EMBERBSD_HOST_ROLLUP);\n')
    (jsdir/'build/ninja/write-if-changed.js').write_text('')
    with (fixture/'BUILD.gn').open('a') as build: build.write('node_action("js") { script="scripts/test.js" outputs=["$target_gen_dir/js-result"] args=[rebase_path(outputs[0],root_build_dir)] }\n')
    (fixture/'mini.ts').write_text('export const value = 1;\n')
    (fixture/'action.py').write_text('import os,sys\nsys.path.insert(0,os.path.join(os.path.dirname(__file__),"../third_party/node"))\nimport node,node_modules\na=node.RunNode([node_modules.PathToTypescript()]).strip()\nb=node.RunNode([node_modules.PathToRollup()]).strip()\nopen(sys.argv[1],"w").write(a+"/"+b+"/"+os.environ["EMBERBSD_HOST_NODE"])\n')
    helper=tree/'third_party/node/run_selected_providers.py'
    real_versions=run([sys.executable,helper,'--inspect',host/'bin/node',host/'bin/tsc',host/'bin/rollup'],cwd=tree,env=base_env).splitlines()
    assert len(real_versions)==3 and all(real_versions)
    scripts=[]
    for item in ('ts1','ts2','roll1','roll2'):
        folder=root/item;folder.mkdir();(folder/'package.json').write_text(json.dumps({'name':'typescript' if item.startswith('ts') else 'rollup','version':'1.0.0'}))
        path=folder/'entry.js';path.write_text('console.log('+json.dumps(item)+')\n');os.utime(path,(1,1));scripts.append(path)
    alias=root/'node-alias';alias.symlink_to(host/'bin/node')
    node=str(host/'bin/node');out=root/'out'
    def generate(node_path,ts,roll):
        env=dict(base_env,EMBERBSD_HOST_NODE=str(node_path),EMBERBSD_HOST_TYPESCRIPT=str(ts),EMBERBSD_HOST_ROLLUP=str(roll))
        helper=tree/'third_party/node/run_selected_providers.py'
        versions=run([sys.executable,helper,'--inspect',node_path,ts,roll],cwd=tree,env=env).splitlines()
        assert len(versions)==3
        out.mkdir(exist_ok=True)
        (out/'args.gn').write_text('emberbsd_node_provider_versions = '+json.dumps(versions)+'\n')
        run([host/'bin/gn','gen',out,'--script-executable='+sys.executable,'--ninja-executable='+str(host/'bin/ninja')],cwd=tree,env=env)
        return env
    def build(env):
        # Deliberately contradict the GN selections; the action argv must win.
        env=dict(env,EMBERBSD_HOST_TYPESCRIPT=str(scripts[0]),EMBERBSD_HOST_ROLLUP=str(scripts[2]),EMBERBSD_HOST_NODE=node)
        return run([host/'bin/ninja','-C',out,'fixture:test','fixture:devtools_test','fixture:js'],cwd=tree,env=env)
    result=out/'gen/fixture/result'
    cases=((node,scripts[0],scripts[2],'ts1','roll1'),
           (node,scripts[1],scripts[2],'ts2','roll1'),
           (node,scripts[1],scripts[3],'ts2','roll2'),
           (alias,scripts[1],scripts[3],'ts2','roll2'))
    for node_path,ts,roll,ts_text,roll_text in cases:
        env=generate(node_path,ts,roll);text=build(env)
        assert 'ACTION' in text, text
        assert result.read_text()==ts_text+'/'+roll_text+'/'+str(node_path)
        assert (out/'gen/fixture/devtools-result').read_text()==result.read_text()
        assert (out/'gen/fixture/js-result').read_text()=='/'.join((str(node_path),str(ts),str(roll)))
        assert 'no work to do' in build(env)
    # Same pathname, changed reported package version: explicit GN regeneration
    # must update commands even when the package metadata has an old mtime.
    version_file=root/'node-version';version_file.write_text(real_versions[0]);os.utime(version_file,(1,1))
    versioned_node=root/'versioned-node'
    versioned_node.write_text('#!'+sys.executable+'\nimport os,sys\nfrom pathlib import Path\n'
        'version='+repr(str(version_file))+'\nnode='+repr(node)+'\n'
        'if sys.argv[1:] == ["--version"]: print(Path(version).read_text().strip())\n'
        'else: os.execv(node,[node,*sys.argv[1:]])\n')
    versioned_node.chmod(0o755);os.utime(versioned_node,(1,1))
    env=generate(versioned_node,scripts[1],scripts[3]);assert 'ACTION' in build(env)
    assert 'no work to do' in build(env)
    version_file.write_text('v0.0.0');os.utime(version_file,(1,1))
    env=generate(versioned_node,scripts[1],scripts[3])
    failed=subprocess.run([host/'bin/ninja','-C',out,'fixture:test'],env=env,capture_output=True,text=True)
    assert failed.returncode != 0 and 'ACTION' in failed.stdout and 'selected Node provider version changed' in failed.stdout+failed.stderr
    version_file.write_text(real_versions[0]);os.utime(version_file,(1,1))
    env=generate(versioned_node,scripts[1],scripts[3]);build(env)
    assert 'no work to do' in build(env)
    for index, package in ((1,'typescript'),(3,'rollup')):
        metadata=scripts[index].parent/'package.json'
        metadata.write_text(json.dumps({'name':package,'version':'2.0.0'}));os.utime(metadata,(1,1))
        result.unlink()
        failed=subprocess.run([host/'bin/ninja','-C',out,'fixture:test'],env=env,capture_output=True,text=True)
        assert failed.returncode != 0 and 'selected Node provider version changed' in failed.stdout+failed.stderr
        env=generate(versioned_node,scripts[1],scripts[3]);assert 'ACTION' in build(env)
        assert 'no work to do' in build(env)
    fallback=root/'fallback-out'
    run([host/'bin/gn','gen',fallback,'--script-executable='+sys.executable,'--ninja-executable='+str(host/'bin/ninja')],cwd=tree,env=base_env)
    assert 'run_selected_providers.py' not in (fallback/'toolchain.ninja').read_text()
    config=tree/'BUILDCONFIG.gn';config.write_text(config.read_text().replace('build_with_chromium=true','build_with_chromium=false'))
    run([host/'bin/gn','gen',root/'standalone-out','--script-executable='+sys.executable,'--ninja-executable='+str(host/'bin/ninja')],cwd=tree,env=base_env)
    print('real GN/Ninja: selected Node, TypeScript and Rollup changes rerun older provider inputs; unchanged is no-op')
