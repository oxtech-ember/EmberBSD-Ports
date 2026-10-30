#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise selected Chromium TS7 provider and GN/Ninja input invalidation."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True, help='Chromium source before the tsgo patch')
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--typescript-native-dir', type=Path, required=True)
args = parser.parse_args()
source = args.source.resolve(strict=True)
host = args.host_prefix.resolve(strict=True)
native = args.typescript_native_dir.resolve(strict=True)
patch = Path(__file__).resolve().parents[1] / 'patches/gn-shared-tsgo-inputs.patch'
env = dict(os.environ, PATH=str(host / 'bin') + os.pathsep + str(host / 'sbin'),
           PYTHONDONTWRITEBYTECODE='1', EMBERBSD_HOST_NODE=str(host / 'bin/node'))
with tempfile.TemporaryDirectory(prefix='ember-tsgo-action-') as temporary:
    root = Path(temporary)
    for name in ('build/toolchain', 'third_party/node', 'third_party/typescript'):
        (root / name).mkdir(parents=True)
    for name in ('tsgo.gni', 'typescript.py'):
        shutil.copy2(source / 'third_party/typescript' / name, root / 'third_party/typescript' / name)
    subprocess.run([str(host / 'bin/gpatch'), '--fuzz=0', '-p1', '-d', str(root), '-i', str(patch)],
                   env=env, check=True, stdout=subprocess.DEVNULL)
    shutil.copytree(native, root / 'lib')
    binary, definitions = root / 'lib/tsc', root / 'lib/lib.es5.d.ts'
    env['EMBERBSD_TYPESCRIPT_NATIVE_BINARY'] = str(binary)
    (root / '.gn').write_text('buildconfig = "//build/config.gn"\n')
    (root / 'build/config.gn').write_text('set_default_toolchain("//build/toolchain:host")\n')
    (root / 'build/toolchain/BUILD.gn').write_text('toolchain("host") {\n tool("stamp") { command = "touch {{output}}" }\n}\n')
    (root / 'build/toolchain/rbe.gni').write_text('use_remoteexec = false\n')
    (root / 'third_party/node/node.gni').write_text('emberbsd_host_node = getenv("EMBERBSD_HOST_NODE")\ndeclare_args() {\n emberbsd_typescript_native_binary = ""\n emberbsd_typescript_definitions = []\n}\n')
    (root / 'BUILD.gn').write_text('import("//third_party/typescript/tsgo.gni")\naction("check") {\n script = "//run.py"\n inputs = tsgo_inputs\n outputs = [ "$root_build_dir/result" ]\n args = [ rebase_path(outputs[0], root_build_dir) ]\n}\n')
    (root / 'run.py').write_text('import importlib.util,os,sys\nfrom pathlib import Path\np=Path(__file__).parent/"third_party/typescript/typescript.py"\ns=importlib.util.spec_from_file_location("typescript",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nassert m.GetBinaryPath()==os.environ["EMBERBSD_TYPESCRIPT_NATIVE_BINARY"]\nPath(sys.argv[1]).write_text(m.RunTypeScript(["--version"]))\n')
    out = root / 'out'
    out.mkdir()
    (out / 'args.gn').write_text('emberbsd_typescript_native_binary = "' + str(binary) + '"\n emberbsd_typescript_definitions = [ "' + str(definitions) + '" ]\n')
    subprocess.run([str(host / 'bin/gn'), 'gen', str(out), '--root=' + str(root), '--script-executable=' + str(host / 'bin/python3.15')], env=env, check=True, stdout=subprocess.DEVNULL)
    cmd = [str(host / 'bin/ninja'), '-C', str(out), 'check']
    def run():
        return subprocess.run(cmd, env=env, text=True, capture_output=True, check=True).stdout
    run()
    assert (out / 'result').read_text().startswith('Version ')
    assert 'no work to do' in run()
    for item in (binary, definitions):
        stamp = (out / 'result').stat().st_mtime_ns
        os.utime(item, ns=(stamp + 1_000_000_000, stamp + 1_000_000_000))
        assert 'no work to do' not in run()
        os.utime(item, ns=(1, 1))
print('selected TS7 action and GN/Ninja input invalidation PASS')
