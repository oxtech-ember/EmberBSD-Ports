#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; firmware-only frontend host orchestration checks.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import os
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PROFILE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
ARGS = sdk_source.arguments(sys.argv[1:])
for directory in (PROFILE, PROFILE / 'cross'):
    sys.path.insert(0, str(directory))
import host
import pipeline
import firmware
from target_options import parse, parse_firmware
from emberbsd_sdk.errors import SDKError


class FirmwareTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='firmware-host-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / 'output'
        self.pkgsrc = self.root / 'pkgsrc'
        self.recipe = self.pkgsrc / 'lang/gcc16'
        (self.recipe / 'patches').mkdir(parents=True)
        source_patch = self.recipe / 'patches/patch-gcc_cp_module.cc'
        source_patch.write_bytes(b'modules patch fixture\n')
        self.recipe.joinpath('distinfo').write_text('SHA1 (' + source_patch.name + ') = ' + hashlib.sha1(source_patch.read_bytes()).hexdigest() + '\n')
        self.archive = self.root / 'gcc.tar'
        self.archive.write_bytes(b'audited fixture archive\n')
        source = patch.object(host, 'source_row', return_value=['gcc', '16.2.0', 'fixture', host.sha(self.archive)])
        source.start(); self.addCleanup(source.stop)
        self.tools = self.root / 'tools'
        (self.tools / 'bin').mkdir(parents=True)
        self.executable(self.tools / 'bin/nbgmake', 'exit 97\n')
        self.cc = self.root / 'host-gcc'
        self.cxx = self.root / 'host-g++'
        for compiler in (self.cc, self.cxx):
            self.executable(compiler, "case \"$1\" in -dumpfullversion) echo 16.2.0;; *) echo 'GCC16 host fixture';; esac\n")
        env = patch.dict(os.environ, {'HOST_CC': str(self.cc), 'HOST_CXX': str(self.cxx), 'CROSS_JOBS': '2'}, clear=False)
        env.start(); self.addCleanup(env.stop)
        self.math = self.root / 'math'
        (self.math / 'include').mkdir(parents=True)
        (self.math / 'lib').mkdir()
        for library, macros in {'gmp': [('__GNU_MP_VERSION', 6), ('__GNU_MP_VERSION_MINOR', 3), ('__GNU_MP_VERSION_PATCHLEVEL', 0)], 'mpfr': [('MPFR_VERSION_MAJOR', 4), ('MPFR_VERSION_MINOR', 2), ('MPFR_VERSION_PATCHLEVEL', 2)], 'mpc': [('MPC_VERSION_MAJOR', 1), ('MPC_VERSION_MINOR', 4), ('MPC_VERSION_PATCHLEVEL', 1)]}.items():
            (self.math / 'include' / (library + '.h')).write_text(''.join('#define ' + name + ' ' + str(value) + '\n' for name, value in macros))
            (self.math / 'lib' / ('lib' + library + '.a')).write_bytes(b'host archive fixture')
        self.args = ['--target', 'arm-none-eabi'] + [str(value) for value in (self.pkgsrc, self.archive, self.tools, self.math, self.work)]

    def executable(self, path, body):
        path.write_text('#!/bin/sh\nset -eu\n' + body)
        path.chmod(0o755)

    def test_explicit_finite_target_before_output(self):
        self.assertEqual(parse_firmware(['--target', 'arm-none-eabi', 'input']), ('arm-none-eabi', ['input']))
        for options, message in (([], 'explicit firmware'), (['--target'], 'Unsupported firmware'), (['--target', ''], 'Unsupported firmware'), (['--target', 'aarch64'], 'Unsupported firmware'), (['--target', 'arm-none-eabi', '--target', 'arm-none-eabi'], 'repeated firmware'), (['--kernel'], 'explicit firmware'), (['--unknown'], 'explicit firmware')):
            with self.subTest(options=options), patch.object(pipeline, '_build_binutils', side_effect=AssertionError('Producer reached for rejected target')):
                self.assertRaisesRegex(SDKError, message, firmware.build_main, options + self.args[2:])
                self.assertFalse(self.work.exists())
        for entry in (pipeline.build_main, pipeline.binutils_main):
            self.assertRaises(SDKError, entry, ['--target', 'arm-none-eabi', str(self.work)])
        self.assertEqual(parse([]), ('aarch64', 'applications', []))
        self.assertEqual(parse(['--target', 'amd64', '--kernel', 'input'], True), ('amd64', 'kernel', ['input']))

    def test_bad_host_source_and_math_refuse_before_mkdir(self):
        for path, value, error in ((self.cc, '#!/bin/sh\necho 15.2.0\n', 'GCC 16'), (self.archive, 'wrong archive', 'SHA256'), (self.math / 'include/mpfr.h', '#define MPFR_VERSION_MAJOR 3\n', 'version mismatch')):
            prior = path.read_bytes()
            path.write_text(value)
            with self.subTest(path=path):
                self.assertRaisesRegex(SDKError, error, firmware.build_main, self.args)
                self.assertFalse(self.work.exists())
            path.write_bytes(prior)
        self.assertRaisesRegex(SDKError, 'Unsupported Binutils target', pipeline._build_binutils, 'unknown', str(self.work))
        self.assertFalse(self.work.exists())

    def test_frontend_only_producer_plan(self):
        calls = []
        def logged(argv, log, env=None, cwd=None, **kwargs):
            calls.append(([str(value) for value in argv], Path(log), env, cwd))
            Path(log).write_text('producer intercepted by host fixture\n')
        def binutils(target, work, make_override=None):
            self.assertEqual(target, 'arm-none-eabi')
            self.assertEqual(make_override, self.tools / 'bin/nbgmake')
            root = Path(work); root.mkdir()
            (root / 'inputs.txt').write_text('binutils host fixture\n')
        with patch.object(firmware, 'logged', logged), patch.object(pipeline, '_build_binutils', binutils), patch.object(firmware, 'relocate_binutils'), patch.object(firmware, 'prepare_source'), patch.object(firmware, 'check_compiler', return_value={}), patch.object(firmware, 'assembly_probe'):
            firmware.build_main(self.args)
        configure = next(row for row in calls if row[0][0].endswith('/src/configure'))
        self.assertEqual(set(value for value in configure[0] if value.startswith('--enable-languages=')), {'--enable-languages=c'})
        for required in ('--target=arm-none-eabi', '--without-headers', '--disable-shared', '--disable-threads', '--disable-multilib', '--disable-bootstrap', '--with-cpu=cortex-m4', '--with-mode=thumb', '--with-float=soft'):
            self.assertIn(required, configure[0])
        self.assertFalse(any(value.startswith('--with-sysroot') for value in configure[0]))
        make_calls = [row[0][1:] for row in calls if row[0][0] == str(self.tools / 'bin/nbgmake')]
        self.assertEqual(make_calls, [['-j2', 'all-gcc'], ['install-gcc']])
        self.assertIn('mode=firmware\n', (self.work / 'inputs.txt').read_text())

    def test_cli_refuses_missing_repeated_and_application_targets(self):
        sdk = sdk_source.load()
        for entry, options, message in (
            ('build-firmware.py', [], 'explicit firmware'),
            ('build-firmware.py', ['--target', 'arm-none-eabi', '--target', 'arm-none-eabi'], 'repeated firmware'),
            ('build-firmware.py', ['--target', 'amd64'], 'Unsupported firmware'),
            ('build.py', ['--target', 'arm-none-eabi'], 'Unsupported target'),
            ('build-binutils.py', ['--target', 'arm-none-eabi'], 'Unsupported target')):
            result = subprocess.run([sys.executable, '-I', '-B', str(PROFILE / 'cross' / entry)] + options + ['--sdk-source', sdk], capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(message, result.stderr.decode())
            self.assertFalse(self.work.exists())

    def test_assembly_probe_rejects_wrong_object_machine_and_abi(self):
        tools = {'gcc': self.root / 'arm-none-eabi-gcc', 'readelf': self.root / 'arm-none-eabi-readelf'}
        for index, (machine, abi, accepted) in enumerate(((40, 0x05000000, True), (183, 0x05000000, False), (40, 0, False))):
            work = self.root / ('probe-' + str(index)); work.mkdir()
            def producer(argv, log, **kwargs):
                self.assertEqual([str(value) for value in argv[:8]], [str(tools['gcc']), '-mthumb', '-mcpu=cortex-m4', '-mfloat-abi=soft', '-c', '-x', 'assembler-with-cpp', str(work / 'assembly-check/firmware.S')])
                header = bytearray(52)
                header[:7] = b'\x7fELF\x01\x01\x01'
                struct.pack_into('<HH', header, 16, 1, machine)
                struct.pack_into('<I', header, 36, abi)
                Path(argv[-1]).write_bytes(header)
            with patch.object(firmware, 'logged', producer), patch.object(firmware, 'capture', return_value='ARM EABI fixture attributes'):
                if accepted:
                    firmware.assembly_probe(tools, work)
                    self.assertTrue((work / 'assembly-check/sha256.txt').is_file())
                else:
                    self.assertRaisesRegex(SDKError, 'ARM EABI5', firmware.assembly_probe, tools, work)

    def test_firmware_compiler_rejects_wrong_identity_and_abi(self):
        prefix = self.root / 'prefix'
        (prefix / 'bin').mkdir(parents=True)
        for name in ['gcc'] + host.TOOLS:
            self.executable(prefix / 'bin' / ('arm-none-eabi-' + name), 'exit 97\n')
        macros = ['#define __GNUC__ 16', '#define __ARM_ARCH_7EM__ 1', '#define __thumb__ 1', '#define __SOFTFP__ 1', '#define __SIZEOF_POINTER__ 4']
        def capture(argv, **kwargs):
            option = str(argv[1])
            return {'-dumpmachine': 'arm-none-eabi\n', '-dumpfullversion': '16.2.0\n', '-print-prog-name=as': str(prefix / 'bin/arm-none-eabi-as'), '-print-prog-name=ld': str(prefix / 'bin/arm-none-eabi-ld'), '--version': 'GNU tool 2.47\n'}.get(option, '\n'.join(macros))
        with patch.object(firmware, 'capture', capture):
            firmware.check_compiler(prefix)
            for wrong in ('__ARM_ARCH_7EM__', '__thumb__', '__SOFTFP__', '__SIZEOF_POINTER__'):
                original = list(macros)
                macros[:] = [value for value in macros if not value.startswith('#define ' + wrong + ' ')]
                self.assertRaisesRegex(SDKError, 'ABI mismatch', firmware.check_compiler, prefix)
                macros[:] = original
            for key, bad in (('-dumpmachine', 'aarch64--netbsd'), ('-dumpfullversion', '15.2.0'), ('-print-prog-name=as', '/usr/bin/as'), ('-print-prog-name=ld', '/usr/bin/ld'), ('--version', 'GNU tool 2.42')):
                with patch.object(firmware, 'capture', side_effect=lambda argv, **kw: bad if str(argv[1]) == key else capture(argv, **kw)):
                    self.assertRaises(SDKError, firmware.check_compiler, prefix)
            macros.append('#define __NetBSD__ 1')
            self.assertRaisesRegex(SDKError, 'ABI mismatch', firmware.check_compiler, prefix)


if __name__ == '__main__':
    if ARGS:
        raise SystemExit('Unexpected arguments')
    unittest.main(argv=[sys.argv[0]], verbosity=2)
