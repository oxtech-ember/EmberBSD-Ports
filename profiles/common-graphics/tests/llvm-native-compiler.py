#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check metadata helper inputs with real native tools.
"""Inspect the selected native compiler without building target code."""
import argparse
from pathlib import Path
import shlex
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_sdk as sdk
import llvm_native as native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cxx', required=True)
    parser.add_argument('--llvm-config', required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args(sdk.initialize(sys.argv[1:]))
    triple = sdk.capture(args.llvm_config, '--host-target')
    flags = shlex.split(sdk.capture(args.llvm_config, '--cxxflags'))
    measured = native.compiler(args.cxx, triple, flags)
    assert measured['header_roots'] and len(measured['compiler_libraries']) == 2
    assert all(Path(p).is_file() for p in measured['compiler_libraries'])
    other = 'aarch64-unknown-linux-gnu' if native.machine(triple) == 62 else 'x86_64-unknown-linux-gnu'
    try:
        native.compiler(args.cxx, other, flags)
    except ValueError as error:
        assert 'architectures differ' in str(error), error
    else:
        raise AssertionError('Mismatched compiler architecture accepted')
    if not args.work.is_absolute() or args.work.exists():
        parser.error('--work must be a new absolute directory')
    args.work.mkdir()
    source = args.work / 'probe.cpp'
    source.write_text('#include <llvm/TargetParser/Host.h>\n#include <llvm/Support/raw_ostream.h>\n'
                      'int main() { llvm::outs() << llvm::sys::getDefaultTargetTriple() << "\\n"; }\n')
    libraries = shlex.split(sdk.capture(args.llvm_config, '--link-static', '--libfiles', 'support', 'targetparser'))
    system = shlex.split(sdk.capture(args.llvm_config, '--link-static', '--system-libs', 'support', 'targetparser'))
    linker = shlex.split(sdk.capture(args.llvm_config, '--ldflags'))
    mode = ['-M']
    if measured['family'] == 'gcc':
        mode.insert(0, '-fno-canonical-system-headers')
    sdk.produce([args.cxx, *flags, *mode, str(source), '-MF', str(args.work / 'probe.d')], args.work / 'dependencies.log')
    binary = str(args.work / 'probe')
    sdk.produce([args.cxx, *flags, str(source), *linker, *libraries, *system, '-o', binary], args.work / 'compile.log')
    runtime = native.retain(binary, str(args.work), triple, measured['compiler_libraries'])
    command = [str(args.work / runtime['loader']), '--inhibit-cache', '--library-path', str(args.work / 'native/lib'), binary]
    assert native.machine(sdk.capture(*command)) == native.machine(triple)
    print('PASS: native compiler, real LLVM Support consumer, retained runtime, architecture mismatch refusal')


if __name__ == '__main__':
    main()
