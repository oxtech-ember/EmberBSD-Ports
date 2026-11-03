#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Darwin controller minimum against the macOS-only renderer API."""

import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

OWNER = Path(__file__).resolve().parents[1] / '../../pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron_build', OWNER)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def options(root, prefix, minimum):
    sdk = root / 'MacOSX.sdk'
    sdk.mkdir(exist_ok=True)
    xcode = root / 'XcodeVersion.plist'
    xcode.write_text('fixture')
    work = root / 'work'
    work.mkdir(exist_ok=True)
    return SimpleNamespace(host_prefix=prefix, host_compiler_family='clang',
                           git=prefix / 'bin/git', work=work, macos_sdk=sdk,
                           xcode_version_plist=xcode, macos_minimum=minimum)


with tempfile.TemporaryDirectory(prefix='electron-darwin-minimum-') as temporary:
    root = Path(temporary)
    prefix = root / 'prefix'
    (prefix / 'bin').mkdir(parents=True)
    (prefix / 'libexec').mkdir()
    migcom = prefix / 'libexec/migcom'
    migcom.write_text('fixture')
    migcom.chmod(0o755)

    class Native:
        path = str(prefix / 'bin')
        host = {'os': 'Darwin'}

        @staticmethod
        def tool(name):
            if name == 'python':
                return sys.executable
            return str(prefix / 'bin' / name)

    class HostPrefix:
        @staticmethod
        def load_host_prefix(*args, **kwargs):
            return Native()

    class DarwinSDK:
        @staticmethod
        def read_metadata(sdk_path, *, xcode_version_plist):
            return {'sdk_path': sdk_path}

    class Process:
        @staticmethod
        def sanitized_environment():
            return {}

    provider = SimpleNamespace(select=lambda *_args, **_kwargs: {'environment': {}})
    sdk = {'host_prefix': HostPrefix(), 'darwin_sdk': DarwinSDK(), 'process': Process()}

    with patch.object(build, 'selected_control_git', return_value=str(prefix / 'bin/git')), \
            patch.object(build, 'local_module', return_value=provider), \
            patch.object(build.sys, 'platform', 'darwin'):
        try:
            build.native_inputs(options(root, prefix, '13.9'), sdk)
        except ValueError as error:
            assert str(error) == 'Electron CA renderer requires macOS 14.0 or newer'
        else:
            raise AssertionError('macOS 13 deployment was accepted')
        for minimum in ('14.0', '14.6', '15.0'):
            _native, environment = build.native_inputs(options(root, prefix, minimum), sdk)
            assert environment['MACOSX_DEPLOYMENT_TARGET'] == minimum

print('PASS: Darwin renderer requires macOS 14.0; 14.x and 15.x remain selectable')
