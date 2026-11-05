#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""One provider validation supplies both environment and GN arguments."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

owner = Path(__file__).resolve().parents[1] / '../../pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron_build', owner)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

with tempfile.TemporaryDirectory(prefix='electron-provider-once-') as tmp:
    root = Path(tmp)
    go = root / 'go127/bin/go'
    go.parent.mkdir(parents=True)
    go.write_text('fixture')
    go.chmod(0o755)
    class Native:
        path = str(root / 'bin')
        bundle_root = root
        host = {'os': 'Linux', 'cpu': 'x86_64'}
        def tool(self, role):
            return sys.executable if role == 'python' else str(root / 'bin' / role)
    native = Native()
    class Process:
        def sanitized_environment(self): return {}
        def capture(self, argv, **kwargs):
            if '--inspect' in argv: return SimpleNamespace(stdout=b'node\ntsc\nrollup\n')
            return SimpleNamespace(stdout=b'fixture')
    sdk = {'host_prefix': SimpleNamespace(load_host_prefix=lambda *a, **k: native), 'process': Process()}
    options = SimpleNamespace(host_prefix=root, host_compiler_family='clang', git=root / 'git',
        work=root / 'work', workspace=root / 'workspace', target='amd64', compiler_family='gcc',
        sysroot=root / 'sysroot', sdk_source=root / 'sdk', lock_root=root / 'locks', link_context=root / 'link')
    providers = {'environment': {'EMBERBSD_HOST_TYPESCRIPT': '/tsc', 'EMBERBSD_HOST_ROLLUP': '/rollup'},
                 'arguments': {'emberbsd_node_provider_inputs': ['/provider'], 'fixture_arg': 'value'}}
    calls = []
    def select(n, *, electron=False):
        calls.append((n, electron))
        return providers
    def local_module(_name, filename):
        if filename == 'node-providers.py': return SimpleNamespace(select=select)
        if filename == 'rust-policy.py': return SimpleNamespace(apply=lambda env, _: (env, 'rust-fixture'))
        raise AssertionError(filename)
    tools = {name: '/target/' + name for name in ('cc', 'cxx', 'ar', 'nm', 'readelf', 'strip', 'objcopy')}
    empty_names = ('common_abseil', 'common_icu', 'common_re2', 'common_protobuf', 'common_undici',
                   'common_embedder_sources', 'common_v8_metagen', 'common_node_configure')
    with patch.object(build, 'local_module', side_effect=local_module), \
         patch.object(build, 'selected_control_git', return_value='/git'), \
         patch.object(build, 'devtools_provider_identity', return_value='digest'), \
         patch.object(build, 'target_inputs', return_value=tools), \
         patch.object(build, 'native_runtime_binding', return_value=None), \
         patch.object(build, 'host_buildlink', return_value=None), \
         patch.object(build, 'clang_resource_version', return_value='fixture'):
        with __import__('contextlib').ExitStack() as stack:
            for name in empty_names: stack.enter_context(patch.object(build, name, return_value={}))
            selected, env, args = build.producer_inputs(options, sdk)
            assert selected is native and calls == [(native, True)]
            assert env['EMBERBSD_HOST_TYPESCRIPT'] == '/tsc' and env['EMBERBSD_HOST_ROLLUP'] == '/rollup'
            assert args['fixture_arg'] == 'value'
            assert args['emberbsd_node_provider_inputs'] == ['/provider', str(options.work / 'devtools-provider.json')]
            assert providers['arguments']['emberbsd_node_provider_inputs'] == ['/provider']
            # Independent old public helpers still select and validate themselves.
            calls.clear()
            build.native_inputs(options, sdk)
            build.arguments(options, native, tools, 'rust-fixture', '/launcher')
            assert calls == [(native, True), (native, True)]
            # Exercise the real selector with malformed package metadata.
            real_spec = importlib.util.spec_from_file_location('real_node_providers', owner.parent / 'node-providers.py')
            real = importlib.util.module_from_spec(real_spec)
            real_spec.loader.exec_module(real)
            for name in ('typescript', '@typescript/typescript-linux-x64', 'rollup'):
                directory = root / 'lib/node_modules' / name
                directory.mkdir(parents=True)
                (directory / 'package.json').write_text('{"name":"wrong"}')
            with patch.object(build, 'local_module', return_value=real):
                try: build.producer_inputs(options, sdk)
                except ValueError as error: assert 'wrong selected Node provider' in str(error)
                else: raise AssertionError('malformed provider accepted')
print('PASS: one selection per producer, unchanged public helpers and rejection')
