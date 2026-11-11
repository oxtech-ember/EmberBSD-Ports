#!/usr/bin/env python3
"""Verify pinned Intel BE200 firmware inputs and private package lifecycle."""
# SPDX-License-Identifier: BSD-2-Clause
import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCES = {
    'iwlwifi-gl-c0-fm-c0-100.ucode': (
        'intel/iwlwifi/iwlwifi-gl-c0-fm-c0-100.ucode', 2210748,
        'f8cc54927ae551025a7550cf2117bdda30dc1f392ee925e5c60d80a9cdb0179b'),
    'iwlwifi-gl-c0-fm-c0.pnvm': (
        'intel/iwlwifi/iwlwifi-gl-c0-fm-c0.pnvm', 295036,
        'f481e3b0403ca43a0a444b01c04fa4d1582868afcb026b1e697905f0039ccfa3'),
    'WHENCE': ('WHENCE', 532286,
               '3632c15fcdf114586d53fd782f4e8cbe8e526d52b0dff48b1e83c17e34fc3b38'),
    'LICENCE.iwlwifi_firmware': (
        'LICENSES/LICENCE.iwlwifi_firmware', 2046,
        '16d5040c7cf851fc693b7542e20870935b99802533ea1bfd231c377a2305e5c5'),
}
# iwx(4) asks firmload(9) for the installed names, not the upstream ones.
PAYLOADS = {
    'iwlwifi-gl-c0-fm-c0-100.ucode': 'libdata/firmware/if_iwx/iwx-gl-c0-fm-c0-100',
    'iwlwifi-gl-c0-fm-c0.pnvm': 'libdata/firmware/if_iwx/iwx-gl-c0-fm-c0.pnvm',
    'WHENCE': 'share/doc/iwx-firmware/WHENCE',
    'LICENCE.iwlwifi_firmware':
        'share/licenses/iwx-firmware/LICENCE.iwlwifi_firmware',
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
    with tempfile.TemporaryDirectory(prefix='iwx-firmware-contract-') as tmp:
        root = Path(tmp)
        valid = root / 'valid'
        prepare_flat_inputs(source_root, valid)
        for label, mutate in (
            ('bad hash', lambda d: (d / 'iwlwifi-gl-c0-fm-c0-100.ucode').write_bytes(b'bad')),
            ('bad pnvm hash', lambda d: (d / 'iwlwifi-gl-c0-fm-c0.pnvm').write_bytes(b'bad')),
            ('missing license', lambda d: (d / 'LICENCE.iwlwifi_firmware').unlink()),
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


def verify_installed(prefix, pkg_info, pkgdb, package_name):
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
                   package_name])
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
    verify_inputs = tempfile.TemporaryDirectory(prefix='iwx-firmware-inputs-')
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
    summary = run([str(args.pkg_info), '-X', str(args.package)])
    names = [line.removeprefix('PKGNAME=') for line in summary.splitlines()
             if line.startswith('PKGNAME=')]
    paths = [line.removeprefix('PKGPATH=') for line in summary.splitlines()
             if line.startswith('PKGPATH=')]
    if len(names) != 1 or paths != ['sysutils/iwx-firmware']:
        raise ContractError('archive package identity differs')
    package_name = names[0]
    for cycle in ('install', 'reinstall'):
        run([str(args.pkg_add), '-K', str(pkgdb), '-p', str(prefix), str(args.package)])
        verify_installed(prefix, args.pkg_info, pkgdb, package_name)
        print(cycle + ': PASS')
        if cycle == 'install':
            unexpected = prefix / 'libdata/firmware/if_iwx/unexpected.bin'
            unexpected.write_bytes(b'extra')
            try:
                verify_installed(prefix, args.pkg_info, pkgdb, package_name)
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
