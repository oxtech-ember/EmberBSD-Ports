#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Direct platform protoc and explicit custom runtime remain separate."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
native = SimpleNamespace(host={'os':'Darwin'}, tool=lambda name: '/prefix/bin/' + name)
options = SimpleNamespace(sdk_source=Path('/sdk'), host_compiler_family='clang', host_runtime_root=None)
protoc = Path('/prefix/bin/protoc')
assert build.selected_protoc_command(options, native, protoc, None) == [str(protoc)]
assert build.selected_protoc_command(options, native, protoc, Path('/view')) == [
    '/prefix/bin/python', '/sdk/scripts/run-darwin-with-runtime.py', '--runtime-view', '/view', '--', str(protoc)]
options.host_runtime_root = Path('/custom')
try:
    build.selected_protoc_command(options, native, protoc, None)
    raise AssertionError('custom runtime without scoped view accepted')
except ValueError:
    pass
options.host_runtime_root = None; native.host['os'] = 'Linux'
try:
    build.selected_protoc_command(options, native, protoc, None)
    raise AssertionError('unverified platform accepted')
except ValueError:
    pass
print('PASS: verified Darwin platform direct protoc; custom runtime retains scoped launcher')
