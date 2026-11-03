#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check host PaX role selection without executing build tools."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

controller = Path(__file__).resolve().parents[1] / '../../pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron_controller_pax', controller)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class Native:
    path = '/selected/bin'
    def __init__(self, host): self.host = {'os': host}
    def tool(self, name):
        if name == 'python': return sys.executable
        if name == 'paxctl': return '/selected/bin/paxctl'
        return '/selected/bin/' + name

class HostPrefix:
    def __init__(self, host, missing=False): self.host, self.missing, self.roles = host, missing, None
    def load_host_prefix(self, prefix, *, required_roles, compiler_family):
        self.roles = required_roles
        if self.missing and 'paxctl' in required_roles:
            raise ValueError('selected host prefix has no paxctl')
        return Native(self.host)

class Process:
    @staticmethod
    def sanitized_environment(): return {}

options = SimpleNamespace(host_prefix=Path('/selected'), host_compiler_family='clang', git=Path('/usr/bin/git'), work=Path('/work'))
provider = SimpleNamespace(select=lambda *args, **kwargs: {'environment': {}})
for platform, host in (('darwin', 'Darwin'), ('linux', 'Linux'), ('netbsd10', 'NetBSD')):
    # Darwin's additional SDK checks are unrelated to role selection; the
    # selector itself is exercised directly there, and native_inputs on others.
    roles = build.native_required_roles(platform)
    assert ('paxctl' in roles) == (host == 'NetBSD')
    native = Native(host)
    with patch.object(native, 'tool', wraps=native.tool) as tool:
        got = build.host_paxctl_arguments(native)
        assert got == ({'v8_host_paxctl': '/selected/bin/paxctl'} if host == 'NetBSD' else {})
        assert any(c.args == ('paxctl',) for c in tool.call_args_list) == (host == 'NetBSD')
    if host != 'Darwin':
        selector = HostPrefix(host)
        sdk = {'host_prefix': selector, 'process': Process()}
        with patch.object(build.sys, 'platform', platform), patch.object(build, 'selected_control_git', return_value='/usr/bin/git'), patch.object(build, 'local_module', return_value=provider):
            build.native_inputs(options, sdk)
        assert ('paxctl' in selector.roles) == (host == 'NetBSD')
selector = HostPrefix('NetBSD', missing=True)
with patch.object(build.sys, 'platform', 'netbsd10'):
    try: build.native_inputs(options, {'host_prefix': selector, 'process': Process()})
    except ValueError as error: assert 'no paxctl' in str(error)
    else: raise AssertionError('missing selected host paxctl was accepted')
print('PASS: NetBSD requires and selects prefix paxctl; macOS/Linux do not look it up')
