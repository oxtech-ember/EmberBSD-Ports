#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native esbuild provider selection.
import importlib.util
import json
from pathlib import Path
import tempfile
import sys

file=Path(__file__).resolve().parents[1]/'electron44/files/node-providers.py'
spec=importlib.util.spec_from_file_location('providers',file); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='electron esbuild ') as tmp:
    prefix=Path(tmp);mods=prefix/'lib/node_modules';bin=prefix/'bin';bin.mkdir()
    class Native:
        bundle_root=prefix
        path=str(bin)
        host={'os':'Darwin','cpu':'arm64'}
        def tool(self,name): return str(bin/name)
    def write(path,content):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
    for name,package in [('typescript','typescript'),('@typescript/typescript-darwin-arm64','@typescript/typescript-darwin-arm64'),('rollup','rollup'),('esbuild','esbuild')]:
        write(mods/name/'package.json',json.dumps({'name':package,'version':'1.2.3'}))
    for path in [mods/'typescript/bin/tsc',mods/'@typescript/typescript-darwin-arm64/lib/tsc',mods/'@typescript/typescript-darwin-arm64/lib/lib.d.ts',mods/'rollup/dist/bin/rollup',mods/'esbuild/lib/main.js']:
        write(path,'fixture')
    (bin/'tsc').symlink_to(mods/'typescript/bin/tsc');(bin/'rollup').symlink_to(mods/'rollup/dist/bin/rollup')
    exe=bin/'esbuild';write(exe,'#!'+sys.executable+'\nprint("1.2.3")\n');exe.chmod(0o755)
    values=module.select(Native())['arguments'];assert values['emberbsd_devtools_esbuild_version']=='1.2.3'
    def reject():
        try: module.select(Native())
        except (ValueError,FileNotFoundError): return
        raise AssertionError('invalid selected esbuild accepted')
    metadata=mods/'esbuild/package.json';metadata.write_text(json.dumps({'name':'esbuild','version':'1.2.4'}));reject()
    metadata.write_text(json.dumps({'name':'esbuild','version':'1.2.3'}));(mods/'esbuild/lib/main.js').unlink();reject()
print('native esbuild selection, missing module and version mismatch PASS')
