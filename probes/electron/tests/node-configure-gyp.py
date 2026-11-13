#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check that the Electron controller tracks the selected common GYP input."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

script = Path(__file__).resolve().parents[1] / '../../pkgsrc/devel/electron44/files/build-electron.py'
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
    alternate = root / 'clean-owner'
    for owner_root in (ports, alternate):
        source_owner = owner_root / 'scripts/source-inputs/node/source.py'
        source_owner.parent.mkdir(parents=True, exist_ok=True)
        source_owner.write_text('fixture')
    commands = []
    class OwnerProcess:
        def capture(self, command, **kwargs):
            commands.append(command)
            return SimpleNamespace(stdout=b'{}')
    v8_owner = ports / 'scripts/source-inputs/v8/source.py'
    v8_owner.parent.mkdir(parents=True, exist_ok=True); v8_owner.write_text('fixture')
    options.v8_ports_source, options.v8_pkgsrc = ports, export
    options.node_pkgsrc = export
    options.git = Path('/usr/bin/git')
    options.node_ports_source = alternate
    controller.common_embedder_sources(options, {'process':OwnerProcess()}, Native(), {})
    assert commands[-1][2] == str(alternate / 'scripts/source-inputs/node/source.py')
    helper = alternate / 'scripts/source-inputs/node/configure-inputs.py'
    helper.write_text('selected helper')
    selected = controller.common_node_configure(options, Native(), {'process':Process()}, {}, host/'resource')
    assert selected['emberbsd_node_configure_helper'] == str(helper)
    assert str(helper) in selected['emberbsd_node_configure_dependencies']
    assert str(ports / 'scripts/source-inputs/node/configure-inputs.py') not in selected['emberbsd_node_configure_dependencies']
    helper.unlink()
    try:
        controller.common_node_configure(options, Native(), {'process':Process()}, {}, host/'resource')
    except (FileNotFoundError, ValueError):
        pass
    else:
        raise AssertionError('missing selected Node helper accepted')
    options.node_ports_source = None
    assert controller.common_node_configure(options, Native(), {'process':Process()}, {}, host/'resource') == result
    controller.common_embedder_sources(options, {'process':OwnerProcess()}, Native(), {})
    assert commands[-1][2] == str(ports / 'scripts/source-inputs/node/source.py')
    options.gyp_source = None
    try:
        controller.common_node_configure(options, Native(), {'process': Process()}, {}, host / 'resource')
    except ValueError:
        pass
    else:
        raise AssertionError('missing GYP source accepted')
print('PASS: Electron selects and tracks the common GYP provider')
