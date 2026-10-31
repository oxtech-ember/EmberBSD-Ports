# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Check that a selected native archiver becomes pkgsrc's default tar."""
import importlib.util
from pathlib import Path
import unittest
from types import ModuleType
from unittest import mock

OWNER = Path(__file__).resolve().parents[2]
PATH = OWNER / 'profiles/common-build-tools/cross/prepare-native-tools.py'
spec = importlib.util.spec_from_file_location('prepare_native_tools', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Toolset:
    compiler_family = 'clang'
    path = '/native/bin'
    abi_flags = {name: [] for name in ('cppflags', 'cflags', 'cxxflags', 'ldflags')}

    def __init__(self, include_bsdtar):
        self.tools = {role: '/native/bin/' + role for role in module.ROLE_VARIABLES}
        self.tools.update({role: '/native/bin/' + role for role in module.ROLE_DIRECTORIES})
        if include_bsdtar:
            self.tools['bsdtar'] = '/native/bin/bsdtar'

    def tool(self, role):
        return self.tools[role]

    def command(self, role):
        return (self.tool(role),)


class NativeTarSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = ModuleType('emberbsd_sdk')
        errors = ModuleType('emberbsd_sdk.errors')
        errors.SDKError = type('SDKError', (Exception,), {})
        cls.modules = mock.patch.dict('sys.modules', {
            'emberbsd_sdk': package, 'emberbsd_sdk.errors': errors,
        })
        cls.modules.start()

    @classmethod
    def tearDownClass(cls):
        cls.modules.stop()

    def test_selected_bsdtar_is_default_tar(self):
        result = module.render(Toolset(True), fetch_mode='manual')
        self.assertIn(b'TOOLS_PLATFORM.tar?= ${_EMBER_SDK_TAR}', result)
        self.assertIn(b'_EMBER_SDK_TAR:= /native/bin/bsdtar', result)

    def test_bootstrap_without_bsdtar_keeps_existing_tar_choice(self):
        result = module.render(Toolset(False), fetch_mode='manual')
        self.assertNotIn(b'TOOLS_PLATFORM.tar?=', result)


if __name__ == '__main__':
    unittest.main()
