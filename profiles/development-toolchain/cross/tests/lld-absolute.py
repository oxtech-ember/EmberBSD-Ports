#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check absolute-symbol duplicate handling in installed LLVM and BFD linkers."""
import argparse
import re
from pathlib import Path
import subprocess
import sys


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--llvm-prefix', required=True, type=Path)
parser.add_argument('--bfd-aarch64-ld', required=True, type=Path)
parser.add_argument('--work', required=True, type=Path)
args = parser.parse_args()

llvm_bin = args.llvm_prefix.resolve() / 'bin'
llvm_mc = llvm_bin / 'llvm-mc'
llvm_as = llvm_bin / 'llvm-as'
lld = llvm_bin / 'ld.lld'
readelf = llvm_bin / 'llvm-readelf'
bfd = args.bfd_aarch64_ld.resolve()
work = args.work.resolve()
work.mkdir(parents=True, exist_ok=False)
failures = []


def run(label, argv, expected_success, diagnostics=()):
    result = subprocess.run([str(arg) for arg in argv], cwd=work,
                            text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    log = work / (label + '.log')
    log.write_text('argv: ' + repr(result.args) + '\n'
                   + 'status: ' + str(result.returncode) + '\n'
                   + result.stdout + result.stderr, encoding='utf-8')
    valid = result.returncode == (0 if expected_success else 1)
    missing = [text for text in diagnostics if text not in result.stderr]
    valid = valid and not missing
    state = 'PASS' if valid else 'FAIL'
    print(f'{state}: {label}: exit={result.returncode}'
          + (f', diagnostic contains {diagnostics!r}' if diagnostics else ''))
    if not valid:
        failures.append(label)
    return result


def assemble(label, triple, source):
    asm = work / (label + '.s')
    obj = work / (label + '.o')
    asm.write_text(source, encoding='utf-8')
    run(label + '-assemble', [llvm_mc, '--triple=' + triple, '-filetype=obj',
                              '-o', obj, asm], True)
    return obj


def absolute_source(value, entry=False):
    lines = ['.globl duplicate_abs_symbol',
             f'.equiv duplicate_abs_symbol, {value}']
    if entry:
        lines = ['.text', '.globl _start', '_start:', '  ret'] + lines
    return '\n'.join(lines) + '\n'


def section_source(entry=False):
    lines = ['.text', '.globl duplicate_section_symbol',
             'duplicate_section_symbol:']
    if entry:
        lines += ['.globl _start', '_start:']
    lines += ['  ret']
    return '\n'.join(lines) + '\n'


def link(label, linker, emulation, objects, expected_success,
         diagnostics=()):
    output = work / (label + '.elf')
    argv = [linker]
    if emulation:
        argv += ['-m', emulation]
    argv += ['-e', '_start', '-o', output, *objects]
    if not expected_success:
        kind = 'duplicate symbol' if linker == lld else 'multiple definition'
        diagnostics = (*diagnostics, kind)
    result = run(label, argv, expected_success, diagnostics)
    if expected_success and result.returncode == 0:
        symbols = run(label + '-readelf',
                      [readelf, '--file-header', '--symbols', output], True)
        expected = 42 if label.endswith('abs42') else 0
        machine = 'AArch64' if label.startswith('aarch64') else 'Advanced Micro Devices X86-64'
        symbol = re.search(r'^\s*\d+:\s*([0-9a-fA-F]+)\s+0\s+NOTYPE\s+GLOBAL\s+DEFAULT\s+ABS\s+duplicate_abs_symbol\s*$',
                           symbols.stdout, re.MULTILINE)
        if (not symbol or int(symbol.group(1), 16) != expected
                or machine not in symbols.stdout):
            failures.append(label + '-elf-metadata')
            print('FAIL: ' + label + ': incorrect ELF symbol or machine')
    return result


for target, triple, emulation in (
        ('x86_64', 'x86_64-unknown-netbsd', 'elf_x86_64'),
        ('aarch64', 'aarch64-unknown-netbsd', 'aarch64elf')):
    inputs = {}
    for label, values in (
            ('abs0', (0, 0)),
            ('abs42', (42, 42)),
            ('abs-conflict', (0, 1))):
        inputs[label] = [
            assemble(f'{target}-{label}-left', triple,
                     absolute_source(values[0], entry=True)),
            assemble(f'{target}-{label}-right', triple,
                     absolute_source(values[1]))]
    inputs['section-zero'] = [
        assemble(f'{target}-section-zero-left', triple,
                 section_source(entry=True)),
        assemble(f'{target}-section-zero-right', triple,
                 section_source())]

    link(f'{target}-lld-abs0', lld, emulation, inputs['abs0'], True)
    link(f'{target}-lld-abs42', lld, emulation, inputs['abs42'], True)
    link(f'{target}-lld-abs-conflict', lld, emulation,
         inputs['abs-conflict'], False, ('duplicate_abs_symbol',))
    link(f'{target}-lld-section-zero', lld, emulation,
         inputs['section-zero'], False, ('duplicate_section_symbol',))

    if target == 'aarch64':
        link('aarch64-bfd-abs0', bfd, None, inputs['abs0'], True)
        link('aarch64-bfd-abs42', bfd, None, inputs['abs42'], True)
        link('aarch64-bfd-abs-conflict', bfd, None,
             inputs['abs-conflict'], False, ('duplicate_abs_symbol',))
        link('aarch64-bfd-section-zero', bfd, None,
             inputs['section-zero'], False, ('duplicate_section_symbol',))

    bitcode = work / f'{target}-strong-global.bc'
    ir = work / f'{target}-strong-global.ll'
    layouts = {
        'x86_64': 'e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-n8:16:32:64-S128',
        'aarch64': 'e-m:e-i8:8:32-i16:16:32-i64:64-i128:128-n32:64-S128',
    }
    ir.write_text('target datalayout = "' + layouts[target] + '"\n'
                  'target triple = "' + triple + '"\n'
                  '@duplicate_abs_symbol = global i32 0\n', encoding='utf-8')
    run(f'{target}-bitcode-assemble', [llvm_as, ir, '-o', bitcode], True)
    link(f'{target}-lld-abs0-bitcode', lld, emulation,
         [inputs['abs0'][0], bitcode], False,
         ('duplicate_abs_symbol', bitcode.name))
    link(f'{target}-lld-bitcode-abs0', lld, emulation,
         [bitcode, inputs['abs0'][0]], False,
         ('duplicate_abs_symbol', bitcode.name))

if failures:
    print('FAIL: ' + ', '.join(failures), file=sys.stderr)
    print('See per-command logs under ' + str(work), file=sys.stderr)
    sys.exit(1)

print('PASS: absolute and regular duplicate-symbol matrix')
