#!/usr/bin/env python3
"""Verify pinned RTL8723D firmware inputs and private package lifecycle."""
# SPDX-License-Identifier: BSD-2-Clause
import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCES = {
    'rtw8723d_fw.bin': ('rtw88/rtw8723d_fw.bin', 28884,
                        '9c64e079815a333a3f7b731be7cc0be65206ebc883891659dc8ff5ed36a5e2f5'),
    'WHENCE': ('WHENCE', 513960,
               'ee6fcbd18f7b69d331ade28de5a7b0b9ba68220e86f26d445679a3f939906353'),
    'LICENCE.rtlwifi_firmware.txt': (
        'LICENSES/LICENCE.rtlwifi_firmware.txt', 2115,
        'a61351665b4f264f6c631364f85b907d8f8f41f8b369533ef4021765f9f3b62e'),
}
PAYLOADS = {
    'rtw8723d_fw.bin': 'libdata/firmware/rtw88/rtw8723d_fw.bin',
    'WHENCE': 'share/doc/rtw88-firmware/WHENCE',
    'LICENCE.rtlwifi_firmware.txt':
        'share/licenses/rtw88-firmware/LICENCE.rtlwifi_firmware.txt',
}


class ContractError(Exception):
    """An expected package contract violation."""


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_distfiles(directory):
    names = {path.name for path in directory.iterdir() if path.is_file()}
    if names != set(SOURCES):
        raise ContractError('distfile names differ: ' + ', '.join(sorted(names)))
    for name, (_, size, expected_hash) in SOURCES.items():
        path = directory / name
        if path.stat().st_size != size or sha256(path) != expected_hash:
            raise ContractError('distfile integrity mismatch: ' + name)


def prepare_flat_inputs(source_root, destination):
    destination.mkdir()
    for name, (relative, _, _) in SOURCES.items():
        source = source_root / relative
        if not source.is_file():
            raise ContractError('source input missing: ' + relative)
        shutil.copyfile(source, destination / name)
    verify_distfiles(destination)


def exercise_faults(source_root):
    with tempfile.TemporaryDirectory(prefix='rtw88-firmware-contract-') as tmp:
        root = Path(tmp)
        valid = root / 'valid'
        prepare_flat_inputs(source_root, valid)
        for label, mutate in (
            ('bad hash', lambda d: (d / 'rtw8723d_fw.bin').write_bytes(b'bad')),
            ('missing license', lambda d: (d / 'LICENCE.rtlwifi_firmware.txt').unlink()),
            ('unexpected filename', lambda d: (d / 'unexpected.bin').write_bytes(b'extra')),
        ):
            candidate = root / label.replace(' ', '-')
            shutil.copytree(valid, candidate)
            mutate(candidate)
            try:
                verify_distfiles(candidate)
            except ContractError:
                continue
            raise ContractError('fault was accepted: ' + label)


def run(command):
    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise ContractError('command failed (' + str(result.returncode) + '): ' +
                            ' '.join(map(str, command)) + '\n' + result.stdout)
    return result.stdout


def verify_installed(prefix, pkg_info, pkgdb):
    actual = {path.relative_to(prefix).as_posix()
              for path in prefix.rglob('*') if path.is_file() or path.is_symlink()}
    expected = set(PAYLOADS.values())
    if actual != expected:
        raise ContractError('installed file list differs: ' + ', '.join(sorted(actual)))
    for name, (_, size, expected_hash) in SOURCES.items():
        path = prefix / PAYLOADS[name]
        if not path.is_file() or path.stat().st_size != size or sha256(path) != expected_hash:
            raise ContractError('installed payload mismatch: ' + str(path))
    listing = run([str(pkg_info), '-K', str(pkgdb), '-L',
                   'rtw88-firmware-48'])
    for relative in PAYLOADS.values():
        full_path = (prefix / relative).as_posix()
        if full_path not in listing:
            raise ContractError('pkg_info omits package payload: ' + full_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-prefix', required=True, type=Path)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--package', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--pkg-add', required=True, type=Path)
    parser.add_argument('--pkg-delete', required=True, type=Path)
    parser.add_argument('--pkg-info', required=True, type=Path)
    args = parser.parse_args()

    if not args.host_prefix.is_absolute() or not args.host_prefix.is_dir():
        raise ContractError('invalid SDK host prefix: ' + str(args.host_prefix))
    host_prefix = args.host_prefix.resolve()
    for tool in (args.pkg_add, args.pkg_delete, args.pkg_info):
        try:
            tool.resolve().relative_to(host_prefix)
        except ValueError as error:
            raise ContractError('package tool is outside SDK prefix: ' + str(tool)) from error
        if not tool.is_file() or not tool.stat().st_mode & 0o111:
            raise ContractError('package tool unavailable: ' + str(tool))
    if args.output.exists():
        raise ContractError('output already exists: ' + str(args.output))
    if not args.inputs.is_dir():
        raise ContractError('source inputs directory missing: ' + str(args.inputs))
    verify_inputs = tempfile.TemporaryDirectory(prefix='rtw88-firmware-inputs-')
    try:
        flat = Path(verify_inputs.name) / 'distfiles'
        prepare_flat_inputs(args.inputs, flat)
        exercise_faults(args.inputs)
    finally:
        verify_inputs.cleanup()
    print('Source integrity and deliberate fault cases: PASS')

    if not args.package.is_file():
        raise ContractError('package archive missing: ' + str(args.package))
    args.output.mkdir(parents=True)
    prefix = args.output / 'prefix'
    pkgdb = args.output / 'pkgdb'
    prefix.mkdir()
    pkgdb.mkdir()
    package_name = 'rtw88-firmware-48'
    for cycle in ('install', 'reinstall'):
        run([str(args.pkg_add), '-K', str(pkgdb), '-p', str(prefix), str(args.package)])
        verify_installed(prefix, args.pkg_info, pkgdb)
        print(cycle + ': PASS')
        if cycle == 'install':
            unexpected = prefix / 'libdata/firmware/rtw88/unexpected.bin'
            unexpected.write_bytes(b'extra')
            try:
                verify_installed(prefix, args.pkg_info, pkgdb)
            except ContractError:
                unexpected.unlink()
            else:
                raise ContractError('unexpected installed filename was accepted')
            print('unexpected installed filename: PASS')
            run([str(args.pkg_delete), '-K', str(pkgdb), '-p', str(prefix), package_name])
            if any((prefix / relative).exists() for relative in PAYLOADS.values()):
                raise ContractError('package removal left firmware payload files')
            print('remove: PASS')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except ContractError as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        sys.exit(1)
