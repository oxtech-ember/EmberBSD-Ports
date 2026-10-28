#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Darwin C++ exception unwinding with the selected LLVM linker."""
import argparse
import os
import re
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--llvm-prefix', type=Path, required=True)
    parser.add_argument('--sysroot', type=Path, required=True)
    parser.add_argument('--ld', type=Path, help='candidate ld64.lld; default is the selected prefix')
    parser.add_argument('--work', type=Path, required=True, help='new scratch directory')
    args = parser.parse_args()
    prefix = args.llvm_prefix.resolve(strict=True)
    compiler = prefix / 'bin/clang++'
    linker = args.ld.absolute() if args.ld else prefix / 'bin/ld64.lld'
    if sys.platform != "darwin":
        parser.error("this test requires a Darwin host")
    if any(not path.is_file() or not os.access(path, os.X_OK) for path in (compiler, linker)):
        parser.error("selected compiler and linker must be executable files")
    sysroot = args.sysroot.resolve(strict=True)
    work = args.work.absolute()
    work.mkdir(parents=True, exist_ok=False)
    fixtures = {
        'integer': 'int main() { try { throw 7; } catch (int n) { return n == 7 ? 0 : 1; } }\n',
        'runtime-error': '#include <stdexcept>\n#include <string>\nint main() { try { throw std::runtime_error("hello"); } catch (const std::runtime_error &e) { return std::string(e.what()) == "hello" ? 0 : 1; } }\n',
    }
    failures = []
    for name, code in fixtures.items():
        source = work / (name + '.cpp')
        source.write_text(code, encoding='utf-8')
        for sanitizers in ('address', 'function', 'address,function', 'address,undefined'):
            label = name + '-' + sanitizers.replace(',', '-')
            output = work / label
            argv = [str(compiler), '-isysroot', str(sysroot), '-g',
                    '--ld-path=' + str(linker),
                    '-fsanitize=' + sanitizers,
                    str(source), '-o', str(output)]
            build = subprocess.run(argv, text=True, capture_output=True, timeout=120)
            if build.returncode:
                failures.append(label + ' (compile/link)')
                print('FAIL:', label, 'compile/link:', build.stderr, file=sys.stderr)
                continue
            result = subprocess.run([str(output)], text=True, capture_output=True, timeout=30)
            if result.returncode:
                failures.append(label + ' (execution)')
                print('FAIL:', label, 'exit', result.returncode, result.stderr, file=sys.stderr)
            else:
                print('PASS:', label, flush=True)
    # Two temporary local labels, in reverse FDE order, must retain their
    # individual addresses even though neither appears in the input symtab.
    fixture = Path(__file__).with_name('darwin-eh-local-labels.s')
    obj = work / 'local-labels.o'
    executable = work / 'local-labels'
    commands = [
        [str(prefix / 'bin/llvm-mc'), '-filetype=obj',
         '-triple=x86_64-apple-macos10.15', str(fixture), '-o', str(obj)],
        [str(linker), '-arch', 'x86_64', '-platform_version', 'macos',
         '10.15', '27.0', '-syslibroot', str(sysroot), '-lSystem',
         str(obj), '-o', str(executable)],
    ]
    try:
        for command in commands:
            subprocess.run(command, check=True, text=True, capture_output=True,
                           timeout=120)
        symbols = subprocess.run([str(prefix / 'bin/llvm-nm'), '-nm',
                                  str(executable)], check=True, text=True,
                                 capture_output=True, timeout=30).stdout
        frames = subprocess.run([str(prefix / 'bin/llvm-dwarfdump'), '--eh-frame',
                                 str(executable)], check=True, text=True,
                                capture_output=True, timeout=30).stdout
        match = re.search(r'^([0-9a-fA-F]+).* external _main$', symbols, re.M)
        if not match:
            raise ValueError('missing _main symbol')
        main_address = int(match.group(1), 16)
        ranges = {(int(start, 16), int(end, 16)) for start, end in
                  re.findall(r'FDE .*?pc=([0-9a-fA-F]+)\.\.\.([0-9a-fA-F]+)', frames)}
        expected = {(main_address + 4, main_address + 5),
                    (main_address + 8, main_address + 9)}
        if ranges != expected:
            raise ValueError(f'FDE ranges {ranges!r}, expected {expected!r}')
        print('PASS: local-labels', flush=True)
    except (subprocess.CalledProcessError, ValueError) as error:
        failures.append('local-labels')
        print('FAIL: local-labels:', error, getattr(error, 'stderr', ''),
              file=sys.stderr)
    if failures:
        raise SystemExit('exception unwind checks failed: ' + ', '.join(failures))


if __name__ == '__main__':
    main()
