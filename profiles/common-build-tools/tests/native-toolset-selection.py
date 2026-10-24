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

assert type(actual_native_api.NATIVE_TOOLSET_API) is int and actual_native_api.NATIVE_TOOLSET_API == 1


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
        self.abi_flags = {
            'cppflags': ('-isystem', '/declared/native/include'),
            'cflags': ('-fPIC',),
            'cxxflags': ('-fPIC', '-std=c++17'),
            'ldflags': ('-L/declared/native/lib',),
        }

    def tool(self, role):
        return self.tools[role]

    def as_dict(self):
        return {'format': 'emberbsd-native-toolset-selection', 'version': 1,
                'api': 1, 'tools': dict(self.tools),
                'abi_flags': {key: list(value) for key, value in self.abi_flags.items()}}


with tempfile.TemporaryDirectory(prefix='ember-native-selection-') as temporary:
    root = Path(temporary)
    selection = Selection(root / 'selected-sdk')
    archive = root / 'source-fixture'
    archive.write_bytes(b'Explicit source fixture; no LLVM archive or build claim.\n')
    environment = {
        'EMBERBSD_NATIVE_TOOLSET_DESCRIPTOR': str(root / 'descriptor'),
        'EMBERBSD_NATIVE_TOOLSET_DESCRIPTOR_SHA256': 'a' * 64,
        'EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT': str(root / 'qualification'),
        'EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT_SHA256': 'b' * 64,
        'JOBS': '1',
    }
    api = types.ModuleType('emberbsd_sdk.native_toolset')
    api.NATIVE_TOOLSET_API = 1
    api.load_native_toolset = mock.Mock(return_value=selection)
    controller_python = sys.executable

    def command(work, cmake=None, ninja=None):
        return [str(archive), str(work), cmake or selection.tool('cmake'),
                ninja or selection.tool('ninja')]

    def refused(label, values, *, cmake=None, ninja=None, loader_error=None,
                wrong_python=False, external_llvm=None):
        work = root / label
        api.load_native_toolset.reset_mock()
        api.load_native_toolset.side_effect = loader_error
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
        refused('missing-descriptor', {})
        api.load_native_toolset.assert_not_called()
        missing = dict(environment)
        del missing['EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT_SHA256']
        refused('missing-qualification-pin', missing)
        api.load_native_toolset.assert_not_called()
        refused('unqualified-bundle', environment,
                loader_error=SDKError('Producer qualification is not accepted'))
        refused('external-controller-python', environment, wrong_python=True)
        for name in ('HOST_CC', 'HOST_CXX', 'HOST_PYTHON'):
            refused('external-' + name.lower(), dict(environment, **{name: '/outside/tool'}))
        refused('external-cmake', environment, cmake='/outside/cmake')
        refused('external-ninja', environment, ninja='/outside/ninja')
        outside = root / 'outside-llvm-provider'
        outside.mkdir()
        refused('external-native-llvm', environment, external_llvm=outside)
        api.NATIVE_TOOLSET_API = 2
        refused('wrong-api', environment)
        api.load_native_toolset.assert_not_called()
        api.NATIVE_TOOLSET_API = 1
        api.load_native_toolset.side_effect = None

        work = root / 'accepted-controller-fixture'
        runs = []

        def producer(log, argv, cwd=None, env=None):
            runs.append((list(argv), dict(env)))
            if '-S' in argv:
                (work / 'native').mkdir()
            else:
                outputs = work / 'native/bin'
                outputs.mkdir()
                for name in ('llvm-tblgen', 'llvm-min-tblgen', 'llvm-config'):
                    (outputs / name).write_bytes(b'Nonexecuted generator double\n')

        values = dict(environment, CFLAGS='--sysroot=/target-only',
                      CXXFLAGS='-I/target-only', PKG_CONFIG_SYSROOT_DIR='/target-only',
                      PATH='/outside/bin:/usr/bin')
        with mock.patch.dict(os.environ, values, clear=True), \
             mock.patch.object(llvm_host.sys, 'executable', selection.tool('python')), \
             mock.patch.object(llvm_host, 'SOURCE_SHA', hashlib.sha256(archive.read_bytes()).hexdigest()), \
             mock.patch.object(llvm_host, 'extract_source'), \
             mock.patch.object(llvm_host, 'query', return_value='LLVM version 23.1.4'), \
             mock.patch.object(llvm_host, 'log_run', side_effect=producer):
            llvm_host.native('llvm', command(work))
        call = api.load_native_toolset.call_args
        assert call.args == (environment['EMBERBSD_NATIVE_TOOLSET_DESCRIPTOR'],)
        assert call.kwargs['descriptor_sha256'] == 'a' * 64
        assert call.kwargs['accepted_producer_receipt'] == {
            'path': environment['EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT'], 'sha256': 'b' * 64}
        assert set(selection.tools) - {'llvm-config', 'llvm-tblgen'} == set(call.kwargs['required_roles'])
        assert len(runs) == 2
        flags = runs[0][0]
        assert '-DCMAKE_C_COMPILER=' + selection.tool('cc') in flags
        assert '-DCMAKE_CXX_COMPILER=' + selection.tool('cxx') in flags
        assert '-DCMAKE_C_FLAGS=-isystem /declared/native/include -fPIC' in flags
        assert '-DCMAKE_CXX_FLAGS=-isystem /declared/native/include -fPIC -std=c++17' in flags
        assert '-DCMAKE_SHARED_LINKER_FLAGS=-L/declared/native/lib' in flags
        assert not any('/target-only' in flag or '-B/usr/bin' in flag for flag in flags)
        for _, env in runs:
            assert env['PATH'] == str(root / 'selected-sdk')
            assert env['SHELL'] == selection.tool('sh')
            assert env['PKG_CONFIG'] == selection.tool('pkg-config')
            assert all(name not in env for name in ('CFLAGS', 'CXXFLAGS', 'PKG_CONFIG_SYSROOT_DIR'))

    # Use the actual published SDK loader for invalid inputs. These are
    # deliberately incomplete metadata objects, not qualified synthetic bundles.
    adapter_source = Path(__file__).resolve().parents[1] / 'cross/prepare-native-tools.py'
    spec = importlib.util.spec_from_file_location('native_adapter_integration', adapter_source)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    descriptor = root / 'invalid-descriptor.json'
    receipt = root / 'rejected-receipt.json'
    envelope = {'format': 'emberbsd-native-toolset', 'version': 1, 'scope': 'native-build'}
    cases = [
        ('missing-descriptor', None, 'a' * 64, None, 'expected a regular file'),
        ('descriptor-hash', {}, '0' * 64, None, 'SHA256 mismatch'),
        ('descriptor-format', {}, None, None, 'unsupported emberbsd-native-toolset'),
        ('missing-receipt', envelope, None, None, 'expected a regular file'),
        ('rejected-receipt', envelope, None,
         {'format': 'emberbsd-native-toolset-qualification', 'version': 1,
          'scope': 'native-build', 'status': 'FAIL'},
         'producer receipt does not accept this descriptor'),
    ]
    assert sys.modules['emberbsd_sdk.native_toolset'] is actual_native_api
    for label, metadata, wrong_sha, qualification, diagnostic in cases:
        descriptor.unlink(missing_ok=True)
        receipt.unlink(missing_ok=True)
        if metadata is not None:
            descriptor.write_text(json.dumps(metadata))
        digest = wrong_sha or hashlib.sha256(descriptor.read_bytes()).hexdigest()
        if qualification is not None:
            receipt.write_text(json.dumps(qualification))
        receipt_sha = hashlib.sha256(receipt.read_bytes()).hexdigest() if receipt.exists() else 'b' * 64
        environment = {
            'EMBERBSD_NATIVE_TOOLSET_DESCRIPTOR': str(descriptor),
            'EMBERBSD_NATIVE_TOOLSET_DESCRIPTOR_SHA256': digest,
            'EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT': str(receipt),
            'EMBERBSD_NATIVE_TOOLSET_PRODUCER_RECEIPT_SHA256': receipt_sha,
        }
        work = root / ('actual-sdk-' + label)
        with mock.patch.dict(os.environ, environment, clear=True), \
             mock.patch.object(llvm_host, 'query') as query, \
             mock.patch.object(llvm_host, 'log_run') as producer:
            try:
                llvm_host.native('llvm', command(work))
            except SDKError as error:
                assert diagnostic in str(error), (label, str(error))
            else:
                raise AssertionError('Actual SDK admitted invalid LLVM input: ' + label)
            assert not work.exists(), label
            query.assert_not_called()
            producer.assert_not_called()
        destination = root / ('actual-sdk-include-' + label)
        try:
            adapter.main(['publish', '--descriptor', str(descriptor),
                          '--descriptor-sha256', digest,
                          '--producer-receipt', str(receipt),
                          '--producer-receipt-sha256', receipt_sha,
                          '--output', str(destination)])
        except SDKError as error:
            assert diagnostic in str(error), (label, str(error))
        else:
            raise AssertionError('Actual SDK admitted invalid make input: ' + label)
        assert not destination.exists() and not list(root.glob('.native-tools-*'))

print('PASS: eleven double refusals, one LLVM argv fixture and ten actual SDK admission refusals; no tool execution or bundle acceptance')
