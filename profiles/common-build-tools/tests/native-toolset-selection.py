#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check native LLVM selection with SDK API doubles. Never run build tools."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest import mock

sys.dont_write_bytecode = True
from llvm_fixture import load_sdk

sdk, arguments = load_sdk()
if arguments:
    raise SystemExit('Use --sdk-source SOURCE; set TMPDIR for fixture storage')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_host
from emberbsd_sdk.errors import SDKError
from emberbsd_sdk import native_toolset as actual_native_api

assert callable(actual_native_api.load_host_prefix)

# Keep the optional environment compatible with other shared query callers.
with mock.patch('emberbsd_sdk.process.capture',
                return_value=types.SimpleNamespace(stdout=b'23.1.4\n')) as capture:
    assert llvm_host.query(['/selected/tool'], env={'PATH': '/selected'}) == '23.1.4'
    capture.assert_called_once_with(['/selected/tool'], env={'PATH': '/selected'})
    llvm_host.query(['/other/caller'])
    capture.assert_called_with(['/other/caller'], env=None)


class Selection:
    def __init__(self, root):
        roles = ('cc', 'cxx', 'cpp', 'as', 'ld', 'ar', 'ranlib', 'nm', 'strip',
                 'cmake', 'ninja', 'python', 'pkg-config', 'sh')
        self.tools = {}
        root.mkdir()
        for role in roles:
            path = root / role
            path.write_text('Nonexecuted SDK tool double: ' + role + '\n')
            path.chmod(0o755)
            self.tools[role] = str(path)
        llvm = root / 'llvm-native/bin'
        llvm.mkdir(parents=True)
        for role in ('llvm-config', 'llvm-tblgen'):
            path = llvm / role
            path.write_text('Nonexecuted SDK generator double\n')
            self.tools[role] = str(path)
        config = root / 'llvm-native/lib/cmake/llvm'
        config.mkdir(parents=True)
        (config / 'LLVMConfig.cmake').write_text('Nonexecuted LLVM CMake double\n')
        self.path = str(root)
        self.abi_flags = {
            'cppflags': ('-isystem', '/declared/native/include'),
            'cflags': ('-fPIC',),
            'cxxflags': ('-fPIC', '-std=c++17'),
            'ldflags': ('-L/declared/native/lib',),
        }

    def tool(self, role):
        return self.tools[role]

    def command(self, role):
        return (self.tools[role], '-c', '-x', 'assembler') if role == 'as' else (self.tools[role],)

    def as_dict(self):
        return {'format': 'emberbsd-native-toolset-selection', 'version': 1,
                'api': 1, 'tools': dict(self.tools),
                'abi_flags': {key: list(value) for key, value in self.abi_flags.items()}}


with tempfile.TemporaryDirectory(prefix='ember-native-selection-') as temporary:
    root = Path(temporary)
    selection = Selection(root / 'selected-sdk')
    archive = root / 'source-fixture'
    archive.write_bytes(b'Explicit source fixture; no LLVM archive or build claim.\n')
    environment = {'EMBERBSD_HOST_PREFIX': str(root / 'selected-sdk'), 'JOBS': '1'}
    api = types.ModuleType('emberbsd_sdk.native_toolset')
    api.load_host_prefix = mock.Mock(return_value=selection)
    controller_python = sys.executable

    def command(work, cmake=None, ninja=None):
        return [str(archive), str(work), cmake or selection.tool('cmake'),
                ninja or selection.tool('ninja')]

    def refused(label, values, *, cmake=None, ninja=None, loader_error=None,
                wrong_python=False, external_llvm=None):
        work = root / label
        api.load_host_prefix.reset_mock()
        api.load_host_prefix.side_effect = loader_error
        with mock.patch.dict(os.environ, values, clear=True), \
             mock.patch.object(llvm_host.sys, 'executable', controller_python if wrong_python else selection.tool('python')), \
             mock.patch.object(llvm_host, 'SOURCE_SHA', hashlib.sha256(archive.read_bytes()).hexdigest()), \
             mock.patch.object(llvm_host, 'extract_source'), \
             mock.patch.object(llvm_host, 'query', return_value='LLVM version 23.1.4') as query, \
             mock.patch.object(llvm_host, 'log_run') as producer:
            error = None
            try:
                arguments = command(work, cmake, ninja)
                if external_llvm:
                    arguments.insert(1, str(external_llvm))
                llvm_host.native('clang' if external_llvm else 'llvm', arguments)
            except Exception as caught:
                error = caught
            assert not work.exists(), 'Invalid native selection created output: ' + label
            assert isinstance(error, SDKError), 'Invalid native selection accepted: ' + label
            query.assert_not_called()
            producer.assert_not_called()

    with mock.patch.dict(sys.modules, {'emberbsd_sdk.native_toolset': api}):
        refused('missing-prefix', {})
        api.load_host_prefix.assert_not_called()
        refused('invalid-prefix', environment,
                loader_error=SDKError('Missing native GCC16'))
        refused('external-controller-python', environment, wrong_python=True)
        for name in ('HOST_CC', 'HOST_CXX', 'HOST_PYTHON'):
            refused('external-' + name.lower(), dict(environment, **{name: '/outside/tool'}))
        refused('external-cmake', environment, cmake='/outside/cmake')
        refused('external-ninja', environment, ninja='/outside/ninja')
        outside = root / 'outside-llvm-provider'
        outside.mkdir()
        refused('external-native-llvm', environment, external_llvm=outside)
        api.load_host_prefix.side_effect = None

        work = root / 'accepted-controller-fixture'
        runs = []

        def producer(log, argv, cwd=None, env=None):
            runs.append((list(argv), dict(env)))
            if '-S' in argv:
                (work / 'native').mkdir()
            else:
                outputs = work / 'native/bin'
                outputs.mkdir()
                for name in argv[argv.index('-j') + 2:]:
                    (outputs / name).write_bytes(b'Nonexecuted generator double\n')

        values = dict(environment, CFLAGS='--sysroot=/target-only',
                      CXXFLAGS='-I/target-only', PKG_CONFIG_SYSROOT_DIR='/target-only',
                      PATH='/outside/bin:/usr/bin')
        with mock.patch.dict(os.environ, values, clear=True), \
             mock.patch.object(llvm_host.sys, 'executable', selection.tool('python')), \
             mock.patch.object(llvm_host, 'SOURCE_SHA', hashlib.sha256(archive.read_bytes()).hexdigest()), \
             mock.patch.object(llvm_host, 'extract_source'), \
             mock.patch.object(llvm_host, 'query', return_value='23.1.4') as query, \
             mock.patch.object(llvm_host, 'log_run', side_effect=producer):
            llvm_host.native('llvm', command(work))
        call = api.load_host_prefix.call_args
        assert call.args == (environment['EMBERBSD_HOST_PREFIX'],)
        assert set(call.kwargs) == {'required_roles', 'compiler_family'}
        assert call.kwargs['compiler_family'] == 'clang'
        assert set(selection.tools) - {'llvm-config', 'llvm-tblgen'} == set(call.kwargs['required_roles'])
        assert len(runs) == 2
        flags = runs[0][0]
        assert '-DCMAKE_C_COMPILER=' + selection.tool('cc') in flags
        assert '-DCMAKE_CXX_COMPILER=' + selection.tool('cxx') in flags
        assert '-DCMAKE_C_FLAGS=-isystem /declared/native/include -fPIC' in flags
        assert '-DCMAKE_CXX_FLAGS=-isystem /declared/native/include -fPIC -std=c++17' in flags
        assert '-DCMAKE_ASM_FLAGS=-c -x assembler' in flags
        assert '-DCMAKE_SHARED_LINKER_FLAGS=-L/declared/native/lib' in flags
        assert not any('/target-only' in flag or '-B/usr/bin' in flag for flag in flags)
        assert query.call_args_list == [
            mock.call([str(work / 'native/bin' / name), '--version'], env=runs[0][1])
            for name in ('llvm-tblgen', 'llvm-min-tblgen', 'llvm-config')]
        for _, env in runs:
            assert env['PATH'] == str(root / 'selected-sdk')
            assert env['SHELL'] == selection.tool('sh')
            assert env['PKG_CONFIG'] == selection.tool('pkg-config')
            assert all(name not in env for name in ('CFLAGS', 'CXXFLAGS', 'PKG_CONFIG_SYSROOT_DIR'))

        work = root / 'accepted-clang-controller-fixture'
        runs.clear()
        llvm = str(Path(selection.tool('llvm-config')).parents[1])
        with mock.patch.dict(os.environ, dict(values, EMBERBSD_HOST_COMPILER_FAMILY='gcc'), clear=True), \
             mock.patch.object(llvm_host.sys, 'executable', selection.tool('python')), \
             mock.patch.object(llvm_host, 'SOURCE_SHA', hashlib.sha256(archive.read_bytes()).hexdigest()), \
             mock.patch.object(llvm_host, 'extract_source'), \
             mock.patch.object(llvm_host, 'query', return_value='23.1.4') as query, \
             mock.patch.object(llvm_host, 'log_run', side_effect=producer):
            arguments = command(work)
            arguments.insert(1, llvm)
            llvm_host.native('clang', arguments)
        assert set(api.load_host_prefix.call_args.kwargs['required_roles']) == set(selection.tools)
        assert api.load_host_prefix.call_args.kwargs['compiler_family'] == 'gcc'
        assert len(runs) == 2
        assert '-DLLVM_CONFIG=' + selection.tool('llvm-config') in runs[0][0]
        assert '-DLLVM_TABLEGEN=' + selection.tool('llvm-tblgen') in runs[0][0]
        assert query.call_args_list == [
            mock.call([selection.tool('llvm-config'), '--version'], env=runs[0][1]),
            mock.call([str(work / 'native/bin/clang-tblgen'), '--version'], env=runs[0][1])]
        for _, env in runs:
            assert env['PATH'] == selection.path
            assert env['SHELL'] == selection.tool('sh')
            assert env['PKG_CONFIG'] == selection.tool('pkg-config')
            assert all(name not in env for name in ('CFLAGS', 'CXXFLAGS', 'PKG_CONFIG_SYSROOT_DIR'))

    # The shared loader owns path and compiler checks. No descriptor is needed.
    for prefix in ('relative-prefix', str(root / 'missing-prefix')):
        with mock.patch.dict(os.environ, {'EMBERBSD_HOST_PREFIX': prefix}, clear=True), \
             mock.patch.object(llvm_host, 'query') as query, \
             mock.patch.object(llvm_host, 'log_run') as producer:
            try:
                llvm_host.native('llvm', command(root / 'invalid-prefix-output'))
            except (SDKError, FileNotFoundError):
                pass
            else:
                raise AssertionError('Actual SDK accepted an invalid host prefix')
            query.assert_not_called()
            producer.assert_not_called()

print('PASS: native prefix selection, LLVM argv, clean environment and external-tool refusals; no compiler build')
