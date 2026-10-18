#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fixture contracts, not LLVM package acceptance.
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from llvm_fixture import fixture, load_sdk, module, write_json

sdk_source, args = load_sdk()
if len(args) != 2:
    sys.exit('Usage: llvm-stage-reuse.py --sdk-source SDK CMAKE NEW_WORK')
cmake, work = os.path.realpath(args[0]), Path(args[1])
if not work.is_absolute() or work.exists():
    sys.exit('new absolute work directory required')
work.mkdir()
reuse = module('reuse-package-stage')
value = fixture(work, sdk_source, cmake)
config, receipt = work / 'inputs.json', work / 'receipt.json'
write_json(config, value)
reference = work / 'reference'
reference.mkdir()
reuse.record(str(config), str(reference), str(receipt))
receipt_hash = hashlib.sha256(receipt.read_bytes()).hexdigest()
checks = []


def refused(label, expected, function, *arguments):
    try:
        function(*arguments)
    except Exception as error:
        if expected.lower() not in str(error).lower():
            raise AssertionError(f'{label}: wrong failure: {error}') from error
        checks.append(label)
        return
    raise AssertionError(f'{label}: invalid input accepted')


before = reuse.snapshot(value)
dest = work / 'valid'
dest.mkdir()
reuse.install(str(config), str(receipt), receipt_hash, str(dest))
assert '--strip' in json.loads((work / 'last-install-args.json').read_text())
assert reuse.snapshot(value) == before
checks.append('valid CMake install preserves original source and objects')
assert (dest / 'usr/pkg/include/llvm/IR/Empty.h').read_bytes() == b''
checks.append('valid empty installed file')
for kind in ('recipe', 'sdk_recipe'):
    destination = Path(value[kind]) / 'private-stage'
    destination.mkdir()
    invocations = (work / 'install-invocations.log').read_bytes()
    refused(kind + ' destination overlap', 'overlaps LLVM inputs', reuse.install, str(config), str(receipt), receipt_hash, str(destination))
    assert (work / 'install-invocations.log').read_bytes() == invocations and not list(destination.iterdir())
for kind in ('source', 'build', 'recipe', 'sdk_recipe'):
    output = Path(value[kind]) / 'rejected-receipt.json'
    destination = work / ('record-overlap-' + kind)
    destination.mkdir()
    invocations = (work / 'install-invocations.log').read_bytes()
    refused(kind + ' receipt overlap', 'Receipt overlaps LLVM inputs', reuse.record, str(config), str(destination), str(output))
    assert not output.exists() and not list(destination.iterdir()) and (work / 'install-invocations.log').read_bytes() == invocations
for label, path in zip(('source', 'patch', 'compiler', 'native-tool', 'object', 'normalized-plist', 'target-ABI-header'),
    (value['source'] + '/runtime.dat', value['recipe'] + '/patch', str(work / 'bin/gcc'), str(work / 'bin/tblgen'), value['build'] + '/object.dat', value['manifests']['full'], str(work / 'target-abi.h'))):
    path = Path(path)
    original = path.read_bytes()
    path.write_bytes(original + b'changed')
    refused(label + ' drift', 'drift', reuse.verify, str(config), str(receipt), receipt_hash)
    path.write_bytes(original)
for path in (Path(value['build']) / 'object.dat', work / 'bin/gcc'):
    mode = path.stat().st_mode & 0o7777
    path.chmod(mode ^ 0o100)
    refused(path.name + ' mode drift', 'drift', reuse.verify, str(config), str(receipt), receipt_hash)
    path.chmod(mode)
for label, key, new, expected in [('flag', 'flags', {'CXXFLAGS': '-O0'}, 'contract differs'), ('ABI', 'target', dict(value['target'], triple='x86_64--netbsd'), 'target ABI'), ('install strip mode', 'install_strip', False, 'contract differs')]:
    changed = copy.deepcopy(value)
    changed[key] = new
    write_json(config, changed)
    refused(label + ' drift', expected, reuse.verify, str(config), str(receipt), receipt_hash)
write_json(config, value)
original = receipt.read_bytes()
receipt.write_bytes(original + b' ')
refused('receipt drift', 'receipt drift', reuse.verify, str(config), str(receipt), receipt_hash)
receipt.write_bytes(original)
(work / 'incomplete').mkdir()
os.environ['LLVM_REUSE_TEST_MUTATE'] = 'missing'
refused('incomplete full stage', 'command', reuse.record, str(config), str(work / 'incomplete'), str(work / 'invalid-receipt.json'))
os.environ.pop('LLVM_REUSE_TEST_MUTATE')
assert not (work / 'invalid-receipt.json').exists()
obj = Path(value['build']) / 'object.dat'
for mode in ('aba', 'missing', 'after', 'outside'):
    dest = work / ('install-' + mode)
    dest.mkdir()
    original = obj.read_bytes()
    os.environ['LLVM_REUSE_TEST_MUTATE'] = mode
    refused(mode + ' during install', {'after': 'drift', 'outside': 'outside the target prefix'}.get(mode, 'Installed LLVM stage differs'), reuse.install, str(config), str(receipt), receipt_hash, str(dest))
    os.environ.pop('LLVM_REUSE_TEST_MUTATE')
    obj.write_bytes(original)
original = obj.read_bytes()
elf = bytearray(64)
elf[:7] = b'\x7fELF\x02\x01\x01'
elf[16:18] = (3).to_bytes(2, 'little')
elf[18:20] = (183).to_bytes(2, 'little')
elf[20:24] = (1).to_bytes(4, 'little')
elf[52:54] = (64).to_bytes(2, 'little')
obj.write_bytes(elf)
(work / 'valid-elf').mkdir()
reuse.record(str(config), str(work / 'valid-elf'), str(work / 'valid-elf-receipt.json'))
checks.append('matching AArch64 ELF header')
elf[18:20] = (62).to_bytes(2, 'little')
for label, data, message in [('wrong-elf', elf, 'target header'), ('host-macho', bytes.fromhex('cafebabf') + bytes(16), 'Host Mach-O')]:
    obj.write_bytes(data)
    (work / label).mkdir()
    refused(label + ' reference', message, reuse.record, str(config), str(work / label), str(work / (label + '-receipt.json')))
obj.write_bytes(original)
reuse.verify(str(config), str(receipt), receipt_hash)
# Authentic schema-1 data remain readable; no legacy controller is executed.
legacy = copy.deepcopy(value)
legacy['schema'], legacy['perl'] = 1, '/usr/bin/true'
legacy['files']['native_tools'].append('/usr/bin/true')
write_json(work / 'legacy-inputs.json', legacy)
write_json(work / 'legacy-receipt.json', dict(schema=1, context=legacy, inputs=reuse.snapshot(legacy), stage={}))
legacy_hash = hashlib.sha256((work / 'legacy-receipt.json').read_bytes()).hexdigest()
reuse.verify(str(work / 'legacy-inputs.json'), str(work / 'legacy-receipt.json'), legacy_hash)
assert hashlib.sha256((work / 'legacy-receipt.json').read_bytes()).hexdigest() == legacy_hash
checks.append('immutable legacy snapshot verifies without a Ruby controller')
write_json(work / 'results.json', dict(scope='CMake installation and integrity fixtures only; no LLVM package, compiler or hardware acceptance.', checks=checks))
print(f'PASS: {len(checks)} LLVM stage reuse fixture contracts')
