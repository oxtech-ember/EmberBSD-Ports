#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Regression checks for the EmberBSD Meson BUILD/HOST tool contract."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

# Tests run with the SDK's isolated Python mode (-E -S). Add only the Meson
# package shipped in the same selected native prefix as this interpreter.
python_lib = (Path(sys.executable).absolute().parent.parent / 'lib' /
              f'python{sys.version_info.major}.{sys.version_info.minor}' /
              'site-packages')
sys.path.insert(0, str(python_lib))

from mesonbuild.dependencies.pkgconfig import PkgConfigCLI
from mesonbuild.machinefile import parse_machine_files
from mesonbuild.mesonlib import MachineChoice
from mesonbuild.modules import ModuleState
from mesonbuild.options import OptionKey
from mesonbuild.utils.core import EnvironmentVariables


ROOT = Path(__file__).resolve().parent


class MesonBuildHostContract(TestCase):
    def test_find_tool_uses_requested_machine(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = {}
            for role in ('build', 'host'):
                tool = Path(temp) / role / 'wayland-scanner'
                tool.parent.mkdir()
                tool.write_text('#!/bin/sh\nexit 0\n')
                tool.chmod(0o755)
                paths[role] = str(tool)

            class Environment:
                def __init__(self):
                    self.lookups = []

                def lookup_binary_entry(self, machine, name):
                    self.lookups.append((machine, name))
                    return [paths['build' if machine == MachineChoice.BUILD else 'host']]

            environment = Environment()
            interpreter = SimpleNamespace(
                program_from_overrides=lambda *args: None)
            state = ModuleState.__new__(ModuleState)
            state._interpreter = interpreter
            state.environment = environment

            with patch('mesonbuild.modules.ExternalProgram.from_entry',
                       side_effect=lambda name, entry: SimpleNamespace(path=entry[0])):
                native = state.find_tool('wayland-scanner', 'wayland',
                                         'wayland_scanner', native=True)
                target = state.find_tool('wayland-scanner', 'wayland',
                                         'wayland_scanner', native=False)

            self.assertEqual(native.path, paths['build'])
            self.assertEqual(target.path, paths['host'])
            self.assertEqual(environment.lookups, [
                (MachineChoice.BUILD, 'wayland-scanner'),
                (MachineChoice.HOST, 'wayland-scanner')])

    def test_pkg_config_environment_separates_build_and_host(self):
        def make_cli(machine, cross, sysroot, libdirs):
            class Properties:
                def get_sys_root(self):
                    return sysroot

                def get_pkg_config_libdir(self):
                    return libdirs

            env = SimpleNamespace(
                coredata=SimpleNamespace(optstore=SimpleNamespace(
                    get_value_for=lambda key: [])),
                properties={machine: Properties()},
                is_cross_build=lambda: cross,
                get_build_dir=lambda: None)
            cli = PkgConfigCLI.__new__(PkgConfigCLI)
            cli.env = env
            cli.for_machine = machine
            cli.extra_paths = []
            cli.pkgbin = SimpleNamespace(get_command=lambda: ['/selected/pkg-config'])
            return cli

        build_cli = make_cli(MachineChoice.BUILD, True, None,
                             ['/host-prefix/lib/pkgconfig'])
        build_env = build_cli._get_env().get_env({
            'PKG_CONFIG_SYSROOT_DIR': '/inherited/target-sysroot',
            'PKG_CONFIG_LIBDIR': '/inherited/target-pc'})
        self.assertEqual(build_env['PKG_CONFIG_SYSROOT_DIR'], '')
        self.assertEqual(build_env['PKG_CONFIG_LIBDIR'],
                         '/host-prefix/lib/pkgconfig')

        host_cli = make_cli(MachineChoice.HOST, True, '/target/sysroot',
                            ['/target/sysroot/usr/pkg/lib/pkgconfig'])
        host_env = host_cli._get_env().get_env({})
        self.assertEqual(host_env['PKG_CONFIG_SYSROOT_DIR'], '/target/sysroot')
        self.assertEqual(host_env['PKG_CONFIG_LIBDIR'],
                         '/target/sysroot/usr/pkg/lib/pkgconfig')

        native_cli = make_cli(MachineChoice.BUILD, False, None, [])
        native_env = native_cli._get_env().get_env({
            'PKG_CONFIG_SYSROOT_DIR': '/native-configured-sysroot'})
        self.assertEqual(native_env['PKG_CONFIG_SYSROOT_DIR'],
                         '/native-configured-sysroot')

    def test_generated_machine_file_parses_and_preserves_unchanged_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'native.ini'
            tools = {}
            for name in ('c', 'cpp', 'ar', 'ranlib', 'nm', 'strip', 'pkg-config'):
                tool = root / 'tools' / name
                tool.parent.mkdir(exist_ok=True)
                tool.write_text('#!/bin/sh\nexit 0\n')
                tool.chmod(0o755)
                tools[name] = str(tool)

            command = [sys.executable, str(ROOT / 'files/native-file.py'),
                       '--output', str(output)]
            command.extend('--binary=' + name + '=' + path
                           for name, path in tools.items())
            command.extend([
                '--pkg-config-libdir=' + str(root / 'host lib/pkgconfig'),
                '--cflags=-I' + str(root / 'host-include'),
                '--cppflags=-DHOST_ROLE=1',
                '--cxxflags=-std=c++17',
                '--ldflags=-L' + str(root / 'host-lib')])
            subprocess.run(command, check=True)

            parsed = parse_machine_files([str(output)], str(root))
            binaries = parsed['binaries']
            self.assertEqual(binaries['c'], tools['c'])
            self.assertEqual(binaries['pkg-config'], tools['pkg-config'])
            self.assertEqual(parsed['properties']['pkg_config_libdir'],
                             [str(root / 'host lib/pkgconfig')])
            self.assertEqual(parsed['built-in options']['c_args'],
                             ['-I' + str(root / 'host-include'), '-DHOST_ROLE=1'])

            before_stat = output.stat()
            before_bytes = output.read_bytes()
            subprocess.run(command, check=True)
            after_stat = output.stat()
            self.assertEqual(output.read_bytes(), before_bytes)
            self.assertEqual(after_stat.st_mtime_ns, before_stat.st_mtime_ns)


if __name__ == '__main__':
    main()
