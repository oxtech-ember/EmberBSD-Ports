#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check freestanding tool routing, WASI compatibility and stage refusal paths."""
import argparse
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

files = Path(__file__).resolve().parents[1] / 'files'
sys.path.insert(0, str(files))
import source as owner
import freestanding
import runtime
import wasi

arguments = owner.load_sdk(sys.argv[1:])
argparse.ArgumentParser(description=__doc__).parse_args(arguments)
from emberbsd_sdk import host_prefix, native_checks
from emberbsd_sdk.errors import ProcessOwnershipError, SDKError

prepared = dict(llvm_version='23.1.4', source={'archive': 'shared-llvm'}, recipe={'files': {'patch': 'shared'}})


def refused(action, message):
    try:
        action()
    except SDKError as error:
        assert message in str(error), error
    else:
        raise AssertionError('expected refusal: ' + message)


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary).resolve()
    source = root / 'source'
    for relative in ('LICENSE.TXT', 'CREDITS.TXT', 'lib/builtins/LICENSE.EmberBSD-BINARY128.TXT',
                     'lib/profile/LICENSE.EmberBSD-GCOV.TXT'):
        path = source / 'compiler-rt' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative)
    native = SimpleNamespace(compiler={'version': '23.1.4'}, path='/selected/bin',
        tool=lambda role: sys.executable if role == 'python' else '/selected/bin/' + role)
    cases = (('wasm32-wasip1', 'WASI', 'wasm-ld', 'wasm32-unknown-wasip1'),
             ('riscv32-unknown-elf', 'Generic', 'elf-ld', 'riscv32-unknown-unknown-elf'))
    with patch.object(owner, 'verify_source', return_value=prepared), \
         patch.object(host_prefix, 'load_host_prefix', return_value=native) as load, \
         patch.object(native_checks, 'check_environment', side_effect=lambda *a, **k: k['environment']), \
         patch.object(owner.process, 'capture', return_value=SimpleNamespace(stdout=b'23.1.4\n')):
        for target, system, linker, directory in cases:
            args = SimpleNamespace(source=str(source), git=None, host_prefix='/selected', jobs=3,
                work=str(root / (target + '-work')), stage=str(root / (target + '-stage')))
            commands = []
            def run(command, log, **keywords):
                commands.append(command)
                assert keywords['empty_snapshot_timeout'] == 120
                assert keywords['env']['PATH'] == '/selected/bin'
                if command[-1] == 'install-builtins':
                    archive = Path(args.stage) / 'lib' / directory / 'libclang_rt.builtins.a'
                    archive.parent.mkdir(parents=True)
                    archive.write_bytes(b'!<arch>\nfixture')
            with patch.object(owner.process, 'run_logged', side_effect=run):
                record = (wasi.build(owner, args) if target == 'wasm32-wasip1'
                          else freestanding.build(owner, args, target))
            assert linker in load.call_args.kwargs['required_roles']
            settings = dict(value[2:].split('=', 1) for value in commands[0] if value.startswith('-D'))
            assert settings['CMAKE_SYSTEM_NAME'] == system
            assert settings['CMAKE_LINKER'] == '/selected/bin/' + linker
            assert settings['CMAKE_TRY_COMPILE_TARGET_TYPE'] == 'STATIC_LIBRARY'
            assert settings['COMPILER_RT_BAREMETAL_BUILD'] == 'ON'
            if system == 'WASI':
                assert settings['COMPILER_RT_HAS_FPIC_FLAG'] == 'OFF'
            else:
                assert settings['COMPILER_RT_BUILTINS_ENABLE_PIC'] == 'ON'
                assert 'COMPILER_RT_HAS_FPIC_FLAG' not in settings
            assert list(Path(settings['CMAKE_SYSROOT']).iterdir()) == []
            for language in ('C', 'CXX', 'ASM'):
                assert settings['CMAKE_' + language + '_COMPILER_TARGET'] == target
                flags = settings.get('CMAKE_' + language + '_FLAGS', '')
                if system == 'WASI':
                    assert not flags
                else:
                    assert flags.split() == ['--no-default-config', '-march=rv32imac_zicsr_zifencei',
                                              '-mabi=ilp32', '-ffreestanding']
            assert commands[1][-4:] == ['--parallel', '3', '--target', 'builtins']
            assert record['target'] == target
            verify = lambda: (wasi.verify(owner, args) if target == 'wasm32-wasip1'
                              else freestanding.verify(owner, args, target))
            archive = Path(args.stage) / 'lib' / directory / 'libclang_rt.builtins.a'
            archive.write_bytes(b'changed')
            refused(verify, 'stage changed')
            archive.unlink()
            refused(verify, 'archive is missing')
            archive.write_bytes(b'!<arch>\nfixture')
            assert verify() == record
            manifest = Path(args.stage) / freestanding.PROFILES[target]['manifest']
            manifest.write_bytes(owner.jsonio.json_bytes(dict(record, target='foreign')))
            refused(verify, 'invalid freestanding builtins manifest')
        args.work, args.stage = str(root / 'failed-work'), str(root / 'failed-stage')
        failure = ProcessOwnershipError(123, 'ownership unproven')
        with patch.object(owner.process, 'run_logged', side_effect=failure):
            try:
                freestanding.build(owner, args, 'riscv32-unknown-elf')
            except ProcessOwnershipError as error:
                assert error is failure
            else:
                raise AssertionError('process ownership failure was lost')

cli = (files / 'runtime.py').read_bytes()
assert runtime.build_cli(cli) == runtime.build_cli(cli.replace(b'    freestanding_cli(commands)\n', b''))
print('PASS: WASI/RV32 routing, empty sysroot, stage mutation controls, process failure and OS CLI compatibility')
