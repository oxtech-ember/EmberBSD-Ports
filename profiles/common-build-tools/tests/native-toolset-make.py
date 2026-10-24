#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the make adapter with SDK API doubles and real atomic publication."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import types
from unittest import mock

sys.dont_write_bytecode = True
from llvm_fixture import load_sdk

sdk, arguments = load_sdk()
if arguments:
    raise SystemExit('Use --sdk-source SOURCE; set TMPDIR for fixture storage')
source = Path(__file__).resolve().parents[1] / 'cross/prepare-native-tools.py'
spec = importlib.util.spec_from_file_location('native_make_adapter', source)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
from emberbsd_sdk.errors import SDKError


def refused(function, *arguments):
    try:
        function(*arguments)
    except SDKError:
        return
    raise AssertionError('Invalid native include accepted')


with tempfile.TemporaryDirectory(prefix='ember-native-make-') as temporary:
    root = Path(temporary)
    tools = {role: str(root / ('sdk-' + role)) for role in adapter.ROLE_VARIABLES}
    tools['python'] = sys.executable
    flags = {'cppflags': ('-isystem', '/native/include'), 'cflags': ('-fPIC',),
             'cxxflags': ('-std=c++17',), 'ldflags': ('-L/native/lib',)}
    selected = types.SimpleNamespace(
        tool=lambda role: tools[role], abi_flags=flags,
        as_dict=lambda: {'format': 'emberbsd-native-toolset-selection',
                         'version': 1, 'api': 1, 'tools': dict(tools),
                         'abi_flags': {key: list(value) for key, value in flags.items()}})
    api = types.ModuleType('emberbsd_sdk.native_toolset')
    api.NATIVE_TOOLSET_API = 1
    api.load_native_toolset = mock.Mock(return_value=selected)
    pins = ['--descriptor', str(root / 'descriptor-double'),
            '--descriptor-sha256', 'a' * 64,
            '--producer-receipt', str(root / 'receipt-double'),
            '--producer-receipt-sha256', 'b' * 64]
    destination = root / 'published'
    with mock.patch.dict(sys.modules, {'emberbsd_sdk.native_toolset': api}):
        api.load_native_toolset.side_effect = SDKError('Unqualified producer')
        refused(adapter.main, ['publish', *pins, '--output', str(destination)])
        assert not destination.exists() and not list(root.glob('.native-tools-*'))
        api.load_native_toolset.side_effect = None
        with contextlib.redirect_stdout(io.StringIO()) as output:
            adapter.main(['publish', *pins, '--output', str(destination)])
        result = json.loads(output.getvalue())
        include = Path(result['makeconf'])
        before = include.read_bytes()
        assert hashlib.sha256(before).hexdigest() == result['makeconf_sha256']
        assert not include.stat().st_mode & 0o222
        assert json.loads((destination / 'selection.json').read_bytes()) == selected.as_dict()
        call = api.load_native_toolset.call_args
        assert call.args == (str(root / 'descriptor-double'),)
        assert call.kwargs['descriptor_sha256'] == 'a' * 64
        assert call.kwargs['accepted_producer_receipt'] == {
            'path': str(root / 'receipt-double'), 'sha256': 'b' * 64}
        assert call.kwargs['required_roles'] == tuple(adapter.ROLE_VARIABLES)
        for role in ('bmake', 'gmake', 'xz', 'xzcat', 'install'):
            assert role in call.kwargs['required_roles']
        # A make command-line assignment can replace even := variables.
        # Expected values must be literals, not aliases to another variable.
        for role in adapter.ROLE_VARIABLES:
            name = '_EMBER_SDK_' + role.upper().replace('-', '_')
            assert ('.if "${' + name + '}" != "' + tools[role] + '"').encode() in before
        for name in ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS'):
            assert ('NATIVE_' + name + '?=').encode() in before
            assert ('HOST_' + name + '?=').encode() in before
            assert not any(line.startswith((name + ':=').encode()) for line in before.splitlines())
        commands = dict(line.decode().split(':= ', 1) for line in before.splitlines()
                        if line.startswith(b'_EMBER_NATIVE_') and b'_COMMAND:= ' in line)
        # A configure consumer can use only CC_FOR_BUILD for a complete
        # compile/link. Its ordinary word split must retain both ABI roots.
        argv = shlex.split(commands['_EMBER_NATIVE_CC_COMMAND']) + ['generator.c', '-o', 'generator']
        assert argv == [tools['cc'], '-isystem', '/native/include', '-fPIC',
                        '-L/native/lib', 'generator.c', '-o', 'generator']
        previous = shlex.split(shlex.quote(tools['cc'])) + ['generator.c', '-o', 'generator']
        assert '/native/include' not in previous and '-L/native/lib' not in previous
        cxx = shlex.split(commands['_EMBER_NATIVE_CXX_COMMAND'])
        assert cxx == [tools['cxx'], '-isystem', '/native/include', '-std=c++17', '-L/native/lib']
        for name, value in commands.items():
            assert ('.if "${' + name + '}" != "' + value + '"').encode() in before
        for name, arguments in flags.items():
            value = shlex.join(arguments)
            for variable in ('_EMBER_SDK_' + name.upper(), 'NATIVE_' + name.upper(), 'HOST_' + name.upper()):
                assert ('.if "${' + variable + '}" != "' + value + '"').encode() in before
        assert b'HOST_CC?= ${_EMBER_SDK_CC}' in before
        refused(adapter.publish, selected, str(destination))
        assert include.read_bytes() == before and not list(root.glob('.native-tools-*'))
        verify = ['verify', *pins, '--makeconf', str(include),
                  '--makeconf-sha256', result['makeconf_sha256']]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            adapter.main(verify)
        assert output.getvalue() == 'VERIFIED\n'
        refused(adapter.main, verify[:-1] + ['0' * 64])
        include.chmod(0o644)
        refused(adapter.main, verify)
        include.write_bytes(before + b'# foreign change\n')
        include.chmod(0o444)
        refused(adapter.main, verify[:-1] + [hashlib.sha256(include.read_bytes()).hexdigest()])
        tools['python'] = str(root / 'absent-python')
        try:
            adapter.main(verify)
        except (SDKError, FileNotFoundError):
            pass
        else:
            raise AssertionError('External adapter interpreter accepted')
        tools['python'] = sys.executable
        tools['cc'] = '/injected\n.error unwanted'
        refused(adapter.render, selected)
        for character in ("'", '"', '\\', '$', '#'):
            tools['cc'] = '/unsupported' + character + '/gcc'
            refused(adapter.render, selected)
        tools['cc'] = str(root / 'sdk-cc')
        flags['cppflags'] = ('-DNAME="quoted"',)
        refused(adapter.render, selected)
        assert not list(root.glob('.native-tools-*'))

print('PASS: native make role/ABI argv, thirteen refusals and atomic no-replace fixture; no compiler, bmake or bundle admission')
