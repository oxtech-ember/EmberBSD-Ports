#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the installed npm frontend against the selected common GYP."""
import argparse, os, shutil, subprocess, tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('node-prefix','gyp-source','frontend-dir','python','cc','cxx','make','sdk','xcode-plist','work-dir'):
    p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
for value in vars(a).values():
    if not value.is_absolute(): p.error('all paths must be absolute')
with tempfile.TemporaryDirectory(prefix='node-gyp-common-',dir=a.work_dir) as temporary:
    root=Path(temporary); prefix=root/'prefix'; modules=prefix/'lib/node_modules/npm/node_modules';modules.mkdir(parents=True)
    original=a.node_prefix/'lib/node_modules/npm/node_modules'
    shutil.copytree(original/'node-gyp',modules/'node-gyp',ignore=shutil.ignore_patterns('gyp','__pycache__'))
    for name in ('configure.js','create-config-gypi.js'):
        shutil.copy2(a.frontend_dir/name,modules/'node-gyp/lib'/name)
    for item in original.iterdir():
        if item.name!='node-gyp':os.symlink(item,modules/item.name)
    (prefix/'share').mkdir();os.symlink(a.gyp_source,prefix/'share/gyp')
    (prefix/'include').mkdir();os.symlink(a.node_prefix/'include/node',prefix/'include/node')
    work=root/'addon';work.mkdir();(work/'binding.gyp').write_text('{"targets":[{"target_name":"smoke","sources":["addon.cc"]}]}\n')
    (work/'addon.cc').write_text('#include <node_api.h>\nNAPI_MODULE_INIT() { napi_value v; napi_create_int32(env, 42, &v); napi_set_named_property(env, exports, "value", v); return exports; }\n')
    node=a.node_prefix/'bin/node'; frontend=modules/'node-gyp/bin/node-gyp.js'
    env=dict(os.environ,CC=str(a.cc),CXX=str(a.cxx),MAKE=str(a.make),GYP_MACOS_SDK_PATH=str(a.sdk),GYP_XCODE_VERSION_PLIST=str(a.xcode_plist))
    env.pop('NODE_GYP_SOURCE',None)
    command=[str(node),str(frontend),'configure','--python='+str(a.python)]
    def run(args=(),*,ok=True,contains=None,extra_env=None):
        e=dict(env);e.update(extra_env or {});r=subprocess.run(command+list(args),cwd=work,env=e,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if (r.returncode==0)!=ok or (contains is not None and contains not in r.stdout):raise AssertionError(r.stdout)
        return r.stdout
    out=run();assert str(prefix/'share/gyp/gyp_main.py') in out
    out=run(extra_env={'NODE_GYP_SOURCE':str(a.gyp_source)});assert str(a.gyp_source/'gyp_main.py') in out
    run(['--target=26.0.0'],ok=False,contains='installed Node headers do not match target')
    run(ok=False,contains='NODE_GYP_SOURCE must be an absolute directory',extra_env={'NODE_GYP_SOURCE':'relative'})
    run(ok=False,contains='ENOENT',extra_env={'NODE_GYP_SOURCE':str(root/'missing-gyp')})
    run(['--force-process-config'],ok=False,contains='installed Node headers require their config.gypi')
    bad=root/'bad/include/node';bad.mkdir(parents=True)
    run(['--nodedir='+str(root/'bad')],ok=False,contains='ENOENT')
    (bad/'config.gypi').write_text('{bad json')
    run(['--nodedir='+str(root/'bad')],ok=False,contains='SyntaxError')
    run(['--nodedir='+str(a.node_prefix),'--target=45.3.2'])
    run(['--nodedir='+str(a.node_prefix),'--force-process-config'])
    run(['--nodedir='+str(a.node_prefix)])
    result=subprocess.run([str(node),str(frontend),'build','--jobs=1'],cwd=work,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if result.returncode:raise AssertionError(result.stdout)
    subprocess.run([str(node),'-e','if(require(process.argv[1]).value!==42)process.exit(1)',str(work/'build/Release/smoke.node')],check=True,env=env)
    print('PASS: common GYP, local/default and explicit headers, rejection cases and addon')
