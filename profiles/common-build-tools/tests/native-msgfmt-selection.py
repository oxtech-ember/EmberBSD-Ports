#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the native toolset generator selects only an installed msgfmt."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types

sys.dont_write_bytecode = True


def main():
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(Path(os.environ['EMBERBSD_SDK_SOURCE']) / 'src'))
    adapter_path = root / 'profiles/common-build-tools/cross/prepare-native-tools.py'
    spec = importlib.util.spec_from_file_location('native_tools_adapter', adapter_path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    from emberbsd_sdk import native_toolset

    with tempfile.TemporaryDirectory(prefix='ember-native-msgfmt-') as temporary:
        prefix = Path(temporary) / 'host'
        bindir = prefix / 'bin'
        bindir.mkdir(parents=True)
        msgfmt = bindir / 'msgfmt'
        msgfmt.write_text('#!/bin/sh\nexit 0\n')
        msgfmt.chmod(0o755)

        flags = {name: [] for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags')}

        def load(host_prefix, *, required_roles, compiler_family, abi_flags):
            assert host_prefix == str(prefix)
            assert compiler_family == 'clang'
            assert abi_flags is None
            assert 'msgfmt' in required_roles
            roles = set(required_roles)
            tools = {role: str(bindir / role) for role in roles}
            tools['python'] = sys.executable
            tools['msgfmt'] = str(msgfmt)
            return types.SimpleNamespace(
                compiler_family='clang', path=str(bindir) + os.pathsep + os.environ['PATH'],
                abi_flags=flags, tools=tools,
                tool=lambda role: tools[role], command=lambda role: (tools[role],))

        native_toolset.load_host_prefix = load
        arguments = types.SimpleNamespace(
            host_prefix=str(prefix), compiler_family='clang', fetch_mode='fetch',
            host_abi_cppflags='', host_abi_cflags='', host_abi_cxxflags='', host_abi_ldflags='')
        toolset = adapter.selection(arguments)
        output = adapter.render(toolset).decode()
        assert 'EMBERBSD_BUILD_MSGFMT?= ${_EMBER_SDK_MSGFMT}' in output
        assert '_EMBER_SDK_MSGFMT:= ' + str(msgfmt) in output
        assert 'TOOLS_PLATFORM.msgfmt?= ${_EMBER_SDK_MSGFMT}' not in output

        msgfmt.unlink()
        def load_without_msgfmt(host_prefix, *, required_roles, compiler_family, abi_flags):
            assert 'msgfmt' not in required_roles
            roles = set(required_roles)
            tools = {role: str(bindir / role) for role in roles}
            tools['python'] = sys.executable
            return types.SimpleNamespace(
                compiler_family='clang', path=str(bindir) + os.pathsep + os.environ['PATH'],
                abi_flags=flags, tools=tools,
                tool=lambda role: tools[role], command=lambda role: (tools[role],))

        native_toolset.load_host_prefix = load_without_msgfmt
        output = adapter.render(adapter.selection(arguments)).decode()
        assert 'EMBERBSD_BUILD_MSGFMT' not in output

    print('PASS: generated native include pins present host msgfmt and omits absent msgfmt')


if __name__ == '__main__':
    main()
