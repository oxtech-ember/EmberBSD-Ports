#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Real target metadata and ELF parser guards, without LLVM compilation.
import json
from pathlib import Path
import struct
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_sdk as sdk
import llvm_target as target


def test(args):
    if len(args) != 1:
        raise ValueError('usage: llvm-targets.py --sdk-source SDK NEW_WORK')
    work = Path(sdk.new_destination(args[0]))
    work.mkdir()
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError('FAIL: ' + name)
        checks.append(name)
        print('PASS: ' + name)

    def reject(name, callback):
        try:
            callback()
        except (ValueError, __import__('emberbsd_sdk.errors', fromlist=['SDKError']).SDKError):
            check('rejects ' + name, True)
        else:
            raise ValueError('accepted ' + name)

    for cpu, backend, machine in (('aarch64', 'aarch64', 183), ('x86_64', 'x86', 62)):
        triple = cpu + '-unknown-netbsd'
        cache = dict(CMAKE_SYSTEM_NAME='NetBSD', CMAKE_SYSTEM_PROCESSOR=cpu, LLVM_HOST_TRIPLE=triple, LLVM_DEFAULT_TARGET_TRIPLE=triple)
        definitions = {key: json.dumps(value) for key, value in cache.items() if key.startswith('LLVM_')}
        components = '\n'.join('{ "' + name + '", nullptr, true, {"' + (backend if name == 'native' else '') + '"} }' for name in ('bitwriter', 'engine', 'mcdisassembler', 'mcjit', 'core', 'executionengine', 'scalaropts', 'transformutils', 'instcombine', 'native', 'orcjit', backend))
        spec = target.validate(cache, definitions, components)
        check(cpu + ' metadata binds its own native backend', spec['backend'] == backend and spec['machine'] == machine)
        header = bytearray(64)
        header[:7] = b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HHI', header, 16, 3, machine, 1)
        struct.pack_into('<H', header, 52, 64)
        path = work / (cpu + '.so')
        path.write_bytes(header)
        check(cpu + ' target DSO header accepted', target.validate_elf(path, spec))
        struct.pack_into('<H', header, 18, 62 if machine == 183 else 183)
        path.write_bytes(header)
        reject(cpu + ' mixed ELF architecture', lambda: target.validate_elf(path, spec))
        reject(cpu + ' mixed generated triple', lambda: target.validate(cache, {**definitions, 'LLVM_HOST_TRIPLE': json.dumps('riscv64-unknown-netbsd')}, components))
        reject(cpu + ' foreign target OS', lambda: target.validate({**cache, 'CMAKE_SYSTEM_NAME': 'Darwin'}, definitions, components))
        reject(cpu + ' wrong native backend', lambda: target.validate(cache, definitions, components.replace('{"' + backend + '"}', '{"riscv"}', 1)))
    reject('unsupported processor', lambda: target.for_processor('riscv64'))
    reject('foreign receipt triple', lambda: target.for_triple('x86_64-unknown-linux-gnu'))
    sdk.write_json(work / 'result.json', dict(checks=checks, scope='Generated metadata and actual ELF64 parser only; no target runtime acceptance'))
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(test))
