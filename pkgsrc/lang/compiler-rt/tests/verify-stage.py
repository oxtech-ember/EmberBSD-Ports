#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the public verifier against current recipe identity and synthetic ELF."""
import argparse
import copy
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--sdk-source', required=True)
    cli.add_argument('--git', required=True)
    cli.add_argument('--work', type=Path, required=True)
    args = cli.parse_args()
    args.work.mkdir()
    files = Path(__file__).resolve().parents[1] / 'files'
    owner = module(files / 'source.py', 'verify_source')
    owner.load_sdk(['--sdk-source', args.sdk_source])
    producer = module(files / 'build.py', 'verify_build')
    selected, _ = owner.recipe(args.git)
    stage = args.work / 'stage'
    relative = 'usr/pkg/llvm/lib/clang/23/lib/netbsd/libclang_rt.builtins-aarch64.a'
    archive = stage / relative
    archive.parent.mkdir(parents=True)
    data = bytearray(64)
    data[:7] = b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI', data, 16, 1, 183, 1)
    struct.pack_into('<H', data, 52, 64)
    header = f'{"builtin.o/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode()
    archive.write_bytes(b'!<arch>\n' + header + bytes(data))
    record = dict(format='emberbsd-llvm-runtime', version=1, compiler_family='clang',
        llvm_version=selected['llvm_version'], components=['builtins'], target='aarch64',
        triplet='aarch64--netbsd', machine_arch='aarch64', elf_machine=183, prefix='usr/pkg/llvm',
        source={key: selected['source'][key] for key in ('archive','sha512')},
        recipe=producer.effective_recipe(owner, selected, args.git),
        base=dict(os_revision='a'*40, files={'usr/include/stdint.h':'b'*64}, symlinks={}),
        artifacts=dict(builtins=relative), files={relative:owner.inventory.sha256_file(archive)}, symlinks={})
    manifest = stage/'runtime.json'
    command = [sys.executable, '-B', str(files/'runtime.py'), '--sdk-source', args.sdk_source,
               'verify', '--stage', str(stage), '--target', 'aarch64', '--phase', 'builtins', '--git', args.git]

    def check(value, error=None):
        owner.jsonio.write_json(manifest, value, exclusive=False)
        result = subprocess.run(command, capture_output=True, text=True)
        if error is None:
            assert result.returncode == 0, result.stderr
            assert owner.jsonio.read_json(manifest) == value
        else:
            assert result.returncode != 0 and error in result.stderr, result.stderr

    check(record)
    subset = copy.deepcopy(record)
    subset['recipe']['files'].pop(next(iter(subset['recipe']['files'])))
    check(subset, 'recipe inputs changed')
    wrong_source = copy.deepcopy(record)
    wrong_source['source']['archive'] = 'different-release.tar.xz'
    check(wrong_source, 'source selection changed')
    # The manifest is the stage's key: the verifier does not hash the stage
    # bytes again, while a changed file set still fails.
    changed = bytearray(archive.read_bytes())
    changed[24] = ord('1')  # valid archive metadata, different payload bytes
    archive.write_bytes(changed)
    check(record)
    extra = archive.parent / 'libextra.a'
    extra.write_bytes(bytes(changed))
    check(record, 'inventory changed')
    print('PASS: public verifier accepts current identity by manifest and rejects omitted recipe inputs, wrong source and a changed file set')


if __name__ == '__main__':
    main()
