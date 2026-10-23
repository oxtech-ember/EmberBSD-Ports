#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted). Port of the real-tool Ruby test.
"""Exercise real SPIRV-Tools linker order, validator and imported call targets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files'))
import sdk_source


def make_module(imports, definitions):
    names = [*imports, *definitions]
    text = 'OpCapability Addresses\nOpCapability Linkage\nOpCapability Kernel\nOpMemoryModel Physical64 OpenCL\n'
    text += ''.join(f'OpName %{name} "{name}"\n' for name in names)
    text += ''.join(f'OpDecorate %{name} LinkageAttributes "{name}" Import\n' for name in imports)
    text += ''.join(f'OpDecorate %{name} LinkageAttributes "{name}" Export\n' for name in definitions)
    text += '%void = OpTypeVoid\n%fn = OpTypeFunction %void\n'
    text += ''.join(f'%{name} = OpFunction %void None %fn\nOpFunctionEnd\n' for name in imports)
    for name, callee in definitions.items():
        text += f'%{name} = OpFunction %void None %fn\n%label_{name} = OpLabel\n'
        if callee:
            text += f'%call_{name} = OpFunctionCall %void %{callee}\n'
        text += 'OpReturn\nOpFunctionEnd\n'
    return text


def check(arguments):
    from emberbsd_sdk.errors import CommandError
    from emberbsd_sdk.process import capture
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tools')
    parser.add_argument('output')
    parser.add_argument('--expect-invalid', action='store_true')
    args = parser.parse_args(arguments)
    tools, output = [Path(os.path.abspath(value)) for value in (args.tools, args.output)]
    names = ['spirv-as', 'spirv-link', 'spirv-val', 'spirv-dis']
    if os.path.lexists(output) or not all(os.access(tools / name, os.X_OK) for name in names):
        raise ValueError('Use real SPIRV-Tools and a new output directory')
    output.mkdir(parents=True)
    commands = []

    def run(name, *arguments):
        argv = [str(tools / name), *map(str, arguments)]
        try:
            result = capture(argv)
            text = (result.stdout + result.stderr).decode('utf-8')
            status = 0
        except CommandError as error:
            text = (error.stdout + error.stderr).decode('utf-8')
            status = error.returncode
        commands.append(dict(argv=argv, status=status, output=text))
        return text, status == 0

    def checked(name, *arguments):
        text, valid = run(name, *arguments)
        if not valid:
            raise ValueError(name + ' failed: ' + text)
        return text

    modules = {
        'a': make_module(['ia1', 'ia2'], {'fa': 'ia1'}),
        'b': make_module(['ib1', 'ib2'], {'fb': 'ib2'}),
        'definitions': make_module([], dict.fromkeys(['ia1', 'ia2', 'ib1', 'ib2'])),
        'only_imports': make_module(['ic1', 'ic2'], {}),
    }
    for name, text in modules.items():
        source = output / (name + '.spvasm')
        binary = output / (name + '.spv')
        source.write_text(text)
        checked('spirv-as', '--target-env', 'spv1.3', source, '-o', binary)
        checked('spirv-val', '--target-env', 'spv1.3', binary)
    cases = [
        (['a', 'b'], ['ia1', 'ia2', 'ib1', 'ib2', 'fa', 'fb']),
        (['b', 'a'], ['ib1', 'ib2', 'ia1', 'ia2', 'fb', 'fa']),
        (['a', 'only_imports', 'b'], ['ia1', 'ia2', 'ic1', 'ic2', 'ib1', 'ib2', 'fa', 'fb']),
        (['a', 'b', 'definitions'], ['fa', 'fb', 'ia1', 'ia2', 'ib1', 'ib2']),
        (['definitions'], ['ia1', 'ia2', 'ib1', 'ib2']),
    ]
    invalid = 0
    for index, (inputs, expected) in enumerate(cases):
        binary = output / f'linked-{index}.spv'
        checked('spirv-link', '--target-env', 'spv1.3', '--create-library', '--allow-partial-linkage',
                *(output / (name + '.spv') for name in inputs), '-o', binary)
        validation, valid = run('spirv-val', '--target-env', 'spv1.3', binary)
        if not valid and args.expect_invalid and index < 3 and 'Function declarations must appear before function definitions' in validation:
            invalid += 1
            continue
        if not valid:
            raise ValueError(f'Invalid linked module {index}: {validation}')
        disassembly = checked('spirv-dis', '--no-header', '--raw-id', binary)
        Path(str(binary) + '.txt').write_text(disassembly)
        symbols = dict(re.findall(r'OpName %(\d+) "([^"]+)"', disassembly))
        order = [symbols[name] for name in re.findall(r'%(\d+) = OpFunction ', disassembly)]
        if order != expected:
            raise ValueError(f'Function order {order}, expected {expected}')
        if index < 3:
            calls = [symbols[name] for name in re.findall(r'OpFunctionCall %\d+ %(\d+)', disassembly)]
            expected_calls = ['ia1' if name == 'a' else 'ib2' for name in inputs if name != 'only_imports']
            if calls != expected_calls:
                raise ValueError('Imported call targets changed')
    if args.expect_invalid and invalid != 3:
        raise ValueError(f'Expected three causal validator failures, got {invalid}')
    hashes = {}
    for name in names:
        with (tools / name).open('rb') as stream:
            hashes[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    (output / 'receipt.json').write_text(json.dumps(dict(expected_invalid=args.expect_invalid,
        causal_failures=invalid, cases=len(cases), tools=hashes, commands=commands), indent=2) + '\n')
    print(f'PASS: {len(cases)} linker order cases; {invalid} expected baseline failures')


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    try:
        if sys.version_info[:2] != (3, 15):
            raise ValueError('Host Python 3.15 is required')
        _, arguments = sdk_source.load_sdk()
        check(arguments)
    except Exception as error:
        sdk_source.exit_error(error)
