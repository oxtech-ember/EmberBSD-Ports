#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Build native addons against a selected Node config and prepared headers."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ('host-prefix', 'sdk-source', 'node-source', 'node-gyp-root',
             'lock-root', 'work', 'gyp-source', 'gyp-pkgsrc', 'node-pkgsrc', 'macos-sdk', 'xcode-version-plist'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
for name, value in vars(a).items():
    if not value.is_absolute():
        parser.error('--' + name.replace('_', '-') + ' must be absolute')
host = a.host_prefix.resolve(strict=True)
sdk = a.sdk_source.resolve(strict=True)
source = a.node_source.resolve(strict=True)
graph = a.node_gyp_root.resolve(strict=True)
gyp = a.gyp_source.resolve(strict=True)
node_pkgsrc = a.node_pkgsrc.resolve(strict=True)
gyp_pkgsrc = a.gyp_pkgsrc.resolve(strict=True)
if (graph / 'node_modules/node-gyp/gyp').resolve(strict=True) != gyp:
    parser.error('node-gyp does not use selected common GYP source')
work = a.work.resolve()
if work.exists() or any(work == p or work in p.parents or p in work.parents for p in (host, sdk, source, graph, gyp, node_pkgsrc, gyp_pkgsrc)):
    parser.error('work must be new and disjoint from selected inputs')
sys.path.insert(0, str(sdk / 'src'))
from emberbsd_sdk import process

def tool(name):
    path = (host / 'bin' / name).resolve(strict=True)
    if not path.is_relative_to(host) or not os.access(path, os.X_OK):
        raise ValueError('tool outside selected host prefix: ' + name)
    return str(path)

env = process.sanitized_environment()
env.update(PYTHONDONTWRITEBYTECODE='1', MAKE=tool('gmake'), PATH=str(work/'tools')+':'+str(host/'bin')+':'+str(host/'sbin'),
           HOME=str(work), NODE_PATH=str(graph/'node_modules'), npm_config_python=tool('python3.15'),
           CC=tool('clang'), CXX=tool('clang++'), AR=tool('llvm-ar'), GYP_LIBTOOL=tool('llvm-libtool-darwin'),
           GYP_MACOS_SDK_PATH=str(a.macos_sdk), GYP_XCODE_VERSION_PLIST=str(a.xcode_version_plist))
with process.ContextLocks([str(host), str(source), str(graph), str(gyp), str(node_pkgsrc), str(gyp_pkgsrc), str(sdk)], str(a.lock_root), shared=True), process.ContextLocks([str(work)], str(a.lock_root)):
    node_verifier = Path(__file__).resolve().parents[3] / 'scripts/source-inputs/node/source.py'
    subprocess.run([tool('python3.15'), '-B', str(node_verifier), '--sdk-source', str(sdk),
                    'verify-source', '--source', str(source), '--pkgsrc-root', str(node_pkgsrc)],
                   env=env, check=True, stdout=subprocess.DEVNULL)
    gyp_verify = [tool('python3.15'), '-B', '-I', '-S', str(gyp_pkgsrc/'devel/gyp/files/verify-source.py'),
                  '--sdk-source', str(sdk), '--source', str(gyp), '--pkgsrc-root', str(gyp_pkgsrc)]
    subprocess.run(gyp_verify, env=env, check=True)
    work.mkdir(parents=True)
    aliases = work / 'tools'
    aliases.mkdir()
    for name, executable in {'sed':'gsed', 'touch':'gtouch', 'printf':'gprintf', 'echo':'gecho', 'mkdir':'gmkdir', 'rm':'grm', 'cp':'gcp', 'ln':'gln'}.items():
        (aliases / name).symlink_to(tool(executable))
    for case in ('correct', 'missing', 'mismatch'):
        root=work/case; root.mkdir(); (root/'include').mkdir()
        headers=root/'include/node'; shutil.copytree(host/'include/node',headers)
        shutil.copy2(source/'common.gypi',headers/'common.gypi'); shutil.copy2(source/'src/node.h',headers/'node.h')
        addon=root/'addon'; addon.mkdir()
        (addon/'binding.gyp').write_text('{"targets":[{"target_name":"probe","sources":["probe.cc"]}]}')
        (addon/'probe.cc').write_text('#include <node.h>\nvoid Initialize(v8::Local<v8::Object> exports) {}\nNODE_MODULE(NODE_GYP_MODULE_NAME, Initialize)\n')
        config=headers/'config.gypi'
        data=json.loads('\n'.join(line for line in config.read_text().splitlines() if not line.lstrip().startswith('#')))
        abi=data['variables']['node_module_version']
        if case == 'missing': data['variables'].pop('node_module_version')
        if case == 'mismatch': data['variables']['node_module_version']=abi+1
        config.write_text(json.dumps(data))
        command=[tool('node'),str(graph/'node_modules/node-gyp/bin/node-gyp.js'),'rebuild','--nodedir='+str(root),'--jobs=1','--arch=arm64']
        result=subprocess.run(command,cwd=addon,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=600)
        (root/'build.log').write_text(result.stdout)
        if case == 'correct':
            if result.returncode: raise RuntimeError('correct addon failed; see '+str(root/'build.log'))
            subprocess.run([tool('node'),'-e','require("./build/Release/probe.node")'],cwd=addon,env=env,check=True)
        else:
            expected={'missing':'Native modules require the selected runtime', 'mismatch':'config.gypi module ABI does not match'}[case]
            if result.returncode == 0 or expected not in result.stdout: raise RuntimeError(case+' did not reject config; see '+str(root/'build.log'))
        print(case+' PASS',flush=True)
    root=work/'correct'
    subprocess.run([tool('clang++'),'-fsyntax-only','-std=c++20','-I'+str(root/'include/node'),str(root/'addon/probe.cc')],env=env,check=True)
    subprocess.run(gyp_verify, env=env, check=True)
    print('non-gyp PASS')
