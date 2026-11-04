#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check selected Darwin metadata reaches a real GYP child without discovery."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

sdk_source, prefix, macos_sdk, xcode_plist = map(Path, sys.argv[1:5])
sys.path.insert(0, str(sdk_source / 'src'))
from emberbsd_sdk import darwin_sdk, process
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
class Native:
    host = {'os': 'Darwin', 'cpu': 'arm64'}
    path = str(prefix / 'bin')
    def tool(self, name):
        return sys.executable if name == 'python' else str(prefix / 'bin' / name)
native = Native()
sdk = {'host_prefix': SimpleNamespace(load_host_prefix=lambda *a, **k: native),
       'darwin_sdk': darwin_sdk, 'process': process}
options = SimpleNamespace(host_prefix=prefix, host_compiler_family='clang', git='/usr/bin/git',
                          work=Path('/private/tmp'), macos_sdk=macos_sdk,
                          xcode_version_plist=xcode_plist, macos_minimum='14.0')
build.local_module = lambda *a: SimpleNamespace(select=lambda *a, **k: {'environment': {}})
_, env = build.native_inputs(options, sdk)
assert env['GYP_MACOS_SDK_PATH'] == darwin_sdk.read_metadata(str(macos_sdk), xcode_version_plist=str(xcode_plist))['sdk_path']
assert env['GYP_XCODE_VERSION_PLIST'] == str(xcode_plist.resolve())
script = ("import sys; sys.path.insert(0, sys.argv[1]); import gyp.xcode_emulation as x; "
          "exec('def reject(*a, **k):\\n raise AssertionError(\"unselected host discovery\")'); "
          "x.GetStdoutQuiet = x.GetStdout = reject; print(*x.XcodeVersion())")
command = [sys.executable, '-B', '-c', script, str(prefix / 'share/gyp/pylib')]
missing = dict(env)
missing.pop('GYP_MACOS_SDK_PATH')
missing.pop('GYP_XCODE_VERSION_PLIST')
control = subprocess.run(command, env=missing, text=True, capture_output=True)
assert control.returncode != 0 and 'unselected host discovery' in control.stderr, control.stderr
child = subprocess.run(command, env=env, text=True, capture_output=True, check=True)
assert len(child.stdout.split()) == 2, child.stdout
print('PASS: selected SDK/Xcode metadata reaches real GYP child')
