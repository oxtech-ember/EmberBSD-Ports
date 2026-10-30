#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check that the Electron controller tracks the selected common GYP input."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

script = Path(__file__).resolve().parents[1] / 'electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron_controller', script)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
with TemporaryDirectory() as temporary:
    root = Path(temporary).resolve()
    host, ports, sdk, v8, gyp, export = (root / n for n in ('host', 'ports', 'sdk', 'v8', 'gyp', 'export'))
    paths = [host / 'bin/python', host / 'bin/clang++', host / 'libexec/cwrappers/c++-wrapper',
             host / 'lib/python/site-packages/jinja2/__init__.py',
             host / 'lib/python/site-packages/markupsafe/__init__.py',
             host / 'share/inspector-protocol/emberbsd-prepared-source.json',
             host / 'share/zlib-source/zlib.h', host / 'resource/include/stddef.h',
             ports / 'scripts/source-inputs/node/configure-inputs.py', v8 / 'emberbsd-prepared-source.json',
             gyp / 'emberbsd-prepared-source.json', gyp / 'gyp_main.py',
             export / 'devel/gyp/files/verify-source.py', export / 'EMBERBSD-PKGSRC-REVISION',
             export / 'EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py',
             root / 'libclang', root / 'bindings/clang/cindex.py', root / 'bindings/clang/__init__.py']
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fixture')
    sdk.mkdir()
    class Native:
        def tool(self, name):
            return str(host / ('bin/python' if name == 'python' else 'bin/clang++'))
    class Process:
        def capture(self, *_args, **_kwargs):
            return SimpleNamespace(stdout=str(paths[3]).encode())
    options = SimpleNamespace(node_source=root / 'node', gyp_source=gyp, gyp_pkgsrc=export,
        v8_source=v8, v8_metagen_libclang_so=root / 'libclang', v8_metagen_bindings_dir=root / 'bindings',
        host_prefix=host, ports_source=ports, sdk_source=sdk)
    result = controller.common_node_configure(options, Native(), {'process': Process()}, {}, host / 'resource')
    assert 'gyp-source=' + str(gyp) in result['emberbsd_node_configure_inputs']
    assert 'gyp-pkgsrc=' + str(export) in result['emberbsd_node_configure_inputs']
    assert str(gyp / 'gyp_main.py') in result['emberbsd_node_configure_dependencies']
    assert str(export / 'devel/gyp/files/verify-source.py') in result['emberbsd_node_configure_dependencies']
    options.gyp_source = None
    try:
        controller.common_node_configure(options, Native(), {'process': Process()}, {}, host / 'resource')
    except ValueError:
        pass
    else:
        raise AssertionError('missing GYP source accepted')
print('PASS: Electron selects and tracks the common GYP provider')
