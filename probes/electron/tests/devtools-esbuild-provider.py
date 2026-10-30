#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), selected DevTools esbuild regression.
"""Run the real Chromium bundle template and action with shared esbuild."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'work', 'host-prefix', 'node', 'git'):
    p.add_argument('--'+name, type=Path, required=True)
a = p.parse_args()
assert all(v.is_absolute() for v in vars(a).values()) and not a.work.exists()
a.work.mkdir(parents=True); tree=a.work/'src'; tree.mkdir()
base='third_party/devtools-frontend/src/'
files=[base+'scripts/build/ninja/vars.gni',base+'scripts/build/ninja/bundle.gni',
       base+'scripts/build/esbuild.js',base+'scripts/build/devtools_plugin.js',base+'scripts/devtools_paths.js']
for name in files:
    dest=tree/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.source/name,dest)
patch=Path(__file__).resolve().parents[1]/'patches/gn-devtools-shared-esbuild.patch'
env={'PATH':str(a.host_prefix/'bin')+':'+str(a.host_prefix/'sbin'),'LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1'}
def run(argv, *, fail=False):
    result=subprocess.run(list(map(str,argv)),cwd=tree,env=env,text=True,capture_output=True)
    if (result.returncode != 0) != fail:
        raise AssertionError('command status '+str(result.returncode)+' '+str(argv)+'\n'+result.stdout+result.stderr)
    return result.stdout+result.stderr
run([a.git,'apply','--check',patch]);run([a.git,'apply',patch])
(tree/'.gn').write_text('buildconfig="//build/config.gn"\n')
(tree/'BUILD.gn').write_text('group("default") { deps = [ "//fixture:bundle" ] }\n')
(tree/'build').mkdir(); (tree/'build/config.gn').write_text('host_os="mac"\nhost_cpu="arm64"\nbuild_with_chromium=true\nis_debug=false\nset_default_toolchain("//build:host")\n')
(tree/'build/BUILD.gn').write_text('toolchain("host") { tool("stamp") { command="touch {{output}}" } }\n')
for name,content in [('build/config/devtools.gni','devtools_location="third_party/devtools-frontend/src/"\n'),('build/toolchain/kythe.gni','enable_kythe_annotations=false\n'),(base+'scripts/build/typescript/typescript.gni','')]:
    f=tree/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(content)
nodegni=tree/base/'scripts/build/ninja/node.gni'
nodegni.write_text('''emberbsd_host_node = getenv("EMBERBSD_HOST_NODE")
template("node_action") {
 action(target_name) {
  script = "//run-node.py"
  forward_variables_from(invoker, "*", [ "script", "args" ])
  args = [ "'''+str(a.node)+'''", rebase_path("//third_party/devtools-frontend/src/" + invoker.script, root_build_dir) ] + invoker.args
 }
}
set_defaults("node_action") { inputs = [] args = [] }
''')
(tree/'run-node.py').write_text('import os,sys\nos.execv(sys.argv[1],sys.argv[1:])\n')
(tree/base/'package.json').write_text('{"type":"module"}\n')
(tree/'tools/typescript').mkdir(parents=True);(tree/'tools/typescript/BUILD.gn').write_text('group("copy_package_json") {}\n')
fixture=tree/'fixture';fixture.mkdir();(fixture/'entry.js').write_text('export const answer = 42;\n')
(fixture/'BUILD.gn').write_text('''import("//third_party/devtools-frontend/src/scripts/build/ninja/bundle.gni")
bundle("bundle") {
 entrypoint = "//fixture/entry.js"
 output_file_location = "$target_gen_dir/result.js"
 bundle_all = true
}
''')
module=a.host_prefix/'lib/node_modules/esbuild/lib/main.js';binary=a.host_prefix/'bin/esbuild';metadata=module.parent.parent/'package.json'
version=json.loads(metadata.read_text())['version'];out=tree/'out'
def generate(value):
    args={'emberbsd_devtools_esbuild_module':str(module),'emberbsd_devtools_esbuild_binary':str(binary),'emberbsd_devtools_esbuild_metadata':str(metadata),'emberbsd_devtools_esbuild_version':value}
    env['EMBERBSD_HOST_NODE']=str(a.node)
    run([a.host_prefix/'bin/gn','gen',out,'--root='+str(tree),'--script-executable='+str(a.host_prefix/'bin/python3.15'),'--args='+' '.join(k+'='+json.dumps(v) for k,v in args.items())])
def build(fail=False):return run([a.host_prefix/'bin/ninja','-C',out,'fixture:bundle'],fail=fail)
generate(version); build(); result=out/'gen/fixture/result.js'; assert '42' in result.read_text()
query=run([a.host_prefix/'bin/ninja','-C',out,'-t','query','gen/fixture/result.js'])
for expected in ('lib/node_modules/esbuild/lib/main.js', 'bin/esbuild', 'lib/node_modules/esbuild/package.json'):
    assert expected in query
assert 'no work to do' in build()
generate('0.0.0');failure=build(True);assert 'Selected esbuild version changed' in failure
generate(version);build();assert '42' in result.read_text()
print('Real DevTools bundle GN/Ninja, shared esbuild API, command version invalidation PASS')
