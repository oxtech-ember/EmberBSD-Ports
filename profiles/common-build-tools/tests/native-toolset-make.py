#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the make adapter with SDK API doubles and atomic configuration writes."""
import contextlib
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
        tool=lambda role: tools[role], path=str(root), abi_flags=flags,
        command=lambda role: (tools[role], '-c', '-x', 'assembler') if role == 'as' else (tools[role],),
        compiler_family='clang',
        as_dict=lambda: {'format': 'emberbsd-native-toolset-selection',
                         'version': 1, 'api': 1, 'tools': dict(tools),
                         'abi_flags': {key: list(value) for key, value in flags.items()}})
    api = types.ModuleType('emberbsd_sdk.native_toolset')
    api.load_host_prefix = mock.Mock(return_value=selected)
    pins = ['--host-prefix', str(root / 'host-pkg-llvm')]
    destination = root / 'host-tools.mk'
    with mock.patch.dict(sys.modules, {'emberbsd_sdk.native_toolset': api}):
        api.load_host_prefix.side_effect = SDKError('Missing selected native compiler')
        refused(adapter.main, ['write', *pins, '--output', str(destination)])
        assert not destination.exists() and not list(root.glob('.native-tools-*'))
        api.load_host_prefix.side_effect = None
        with contextlib.redirect_stdout(io.StringIO()) as output:
            adapter.main(['write', *pins, '--output', str(destination)])
        result = json.loads(output.getvalue())
        include = Path(result['makeconf'])
        before = include.read_bytes()
        assert include == destination.resolve()
        assert not (root / 'selection.json').exists()
        call = api.load_host_prefix.call_args
        assert call.args == (str(root / 'host-pkg-llvm'),)
        assert set(call.kwargs) == {'required_roles', 'compiler_family'}
        assert call.kwargs['compiler_family'] == 'clang'
        assert b'EMBERBSD_HOST_COMPILER_FAMILY?= clang\n' in before
        assert call.kwargs['required_roles'] == tuple(adapter.ROLE_VARIABLES)
        for role in ('bmake', 'gmake', 'xz', 'xzcat', 'install', 'fetch'):
            assert role in call.kwargs['required_roles']
        # A make command-line assignment can replace even := variables.
        # Expected values must be literals, not aliases to another variable.
        for role in adapter.ROLE_VARIABLES:
            name = '_EMBER_SDK_' + role.upper().replace('-', '_')
            value = shlex.join(selected.command(role)) if role == 'as' else tools[role]
            assert ('.if "${' + name + '}" != "' + value + '"').encode() in before
        assert ('_EMBER_SDK_AS:= ' + tools['as'] + ' -c -x assembler\n').encode() in before
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
        # Without this mapping pkgsrc selects /usr/bin/curl on Darwin.
        assert b'TOOLS_PLATFORM.fetch?= ${_EMBER_SDK_FETCH}' in before
        assert b'FETCH_USING?= fetch\n' in before
        adapter.write(selected, str(destination))
        assert include.read_bytes() == before and not list(root.glob('.native-tools-*'))
        selected.compiler_family = 'gcc'
        with contextlib.redirect_stdout(io.StringIO()):
            adapter.main(['write', *pins, '--compiler-family', 'gcc', '--output', str(destination)])
        assert api.load_host_prefix.call_args.kwargs['compiler_family'] == 'gcc'
        assert b'EMBERBSD_HOST_COMPILER_FAMILY?= gcc\n' in include.read_bytes()
        selected.compiler_family = 'unknown'
        refused(adapter.render, selected)
        selected.compiler_family = 'clang'
        adapter.write(selected, str(destination))
        verify = ['verify', *pins, '--makeconf', str(include)]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            adapter.main(verify)
        assert output.getvalue() == 'VERIFIED\n'
        include.write_bytes(before + b'# stale mapping\n')
        refused(adapter.main, verify)
        adapter.write(selected, str(include))
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

print('PASS: native make role/ABI argv, prefix selection, stale/foreign mapping refusals and atomic rewrite; no compiler or bmake build')
