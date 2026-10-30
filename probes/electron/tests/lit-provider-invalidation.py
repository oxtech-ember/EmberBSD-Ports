#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise real Chromium Lit GN actions using isolated copies of package inputs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ('graph', 'host-prefix', 'sdk-source', 'environment-json', 'work', 'lock-root'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
graph = a.graph.resolve(strict=True)
host = a.host_prefix.resolve(strict=True)
work = a.work.absolute()
assert not work.exists() and not work.is_relative_to(graph) and not work.is_relative_to(host)
sys.path.insert(0, str(a.sdk_source.resolve(strict=True) / 'src'))
from emberbsd_sdk.process import ContextLocks
config = json.loads(a.environment_json.read_text())
env = config.get('environment', config)
assert env.get('EMBERBSD_HOST_NODE') == str(host / 'bin/node')
modules_source = host / 'lib/node_modules'
names = ('@lit-labs/ssr-dom-shim', '@lit/reactive-element', '@types/trusted-types',
         'lit-html', 'lit-element', 'lit')
with ContextLocks([str(work)], str(a.lock_root)):
    with ContextLocks([str(graph), str(host)], str(a.lock_root), shared=True):
        work.mkdir(parents=True)
        modules = work / 'node_modules'
        for name in names:
            (modules / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(modules_source / name, modules / name, copy_function=shutil.copy2)
        output = work / 'out'
        output.mkdir()
        args = (graph / 'out/args.gn').read_text()
        for name in names:
            args = args.replace(str(modules_source / name) + '/', str(modules / name) + '/')
        old = 'emberbsd_node_modules = "' + str(modules_source) + '"'
        assert old in args
        args = args.replace(old, 'emberbsd_node_modules = "' + str(modules) + '"')
        (output / 'args.gn').write_text(args)
        gn = [str(host / 'bin/gn'), 'gen', str(output), '--root=' + str(graph / 'src'),
              '--script-executable=' + str(host / 'bin/python3.15'),
              '--root-target=//electron', '--root-pattern=//electron:electron']
        ninja = [str(host / 'bin/ninja'), '-C', str(output), '-j', '2',
                 'third_party/lit/v3_0:build_bundle']
        def run(argv):
            return subprocess.run(argv, env=env, cwd=graph / 'src', check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
        run(gn)
        run(ninja)
        assert 'no work to do' in run(ninja)
        metadata = modules / 'lit/package.json'
        package = json.loads(metadata.read_text())
        version = package['version']
        marker = 'lit@' + version
        assert marker in args
        package['version'] = version + '-fixture'
        metadata.write_text(json.dumps(package))
        os.utime(metadata, ns=(1, 1))
        (output / 'args.gn').write_text(args.replace(marker, 'lit@' + package['version']))
        run(gn)
        changed = run(ninja)
        assert ':build_ts' in changed and ':build_bundle' in changed, changed
        declaration = modules / 'lit-html/directives/repeat.d.ts'
        generated = output / 'gen/third_party/lit/v3_0'
        timestamp = max(p.stat().st_mtime_ns for p in generated.rglob('*') if p.is_file())
        os.utime(declaration, ns=(timestamp + 2_000_000_000,) * 2)
        assert ':build_ts' in run(ninja)
print('GN/Ninja Lit version and declaration invalidation PASS')
