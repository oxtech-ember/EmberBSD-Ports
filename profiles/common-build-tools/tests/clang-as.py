#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the installed assembler entry point's argument and exit contract."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--shell', type=Path, required=True)
parser.add_argument('--clang', type=Path, help='Optional declared compiler for a real assembler check')
args = parser.parse_args()
if not args.shell.is_absolute() or not os.access(args.shell, os.X_OK):
    parser.error('--shell must name an executable absolute path')
if args.clang and (not args.clang.is_absolute() or not os.access(args.clang, os.X_OK)):
    parser.error('--clang must name an executable absolute path')
root = Path(__file__).resolve().parents[3]
source = root / 'pkgsrc/lang/clang/files/clang-as.sh'
with tempfile.TemporaryDirectory(prefix='clang-as-') as temporary:
    prefix = Path(temporary)
    (prefix / 'bin').mkdir()
    (prefix / 'bin/mksh').symlink_to(args.shell)
    compiler = prefix / 'bin/clang'
    compiler.write_text('#!' + sys.executable + '\n'
                        'import json, os, sys\n'
                        'print(json.dumps(sys.argv[1:]))\n'
                        'sys.exit(int(os.environ.get("CLANG_AS_STATUS", "0")))\n')
    compiler.chmod(0o755)
    wrapper = prefix / 'bin/clang-as'
    wrapper.write_text(source.read_text().replace('@PREFIX@', str(prefix)))
    wrapper.chmod(0o755)
    cases = [[], ['source.s', '-o', 'object.o'],
             ['space source.s', '-o', 'space object.o'],
             ['--target=aarch64--netbsd', '-Wa,--fatal-warnings', 'input.s'],
             ['semi;colon.s', '$literal', '*literal']]
    for words in cases:
        for status in (0, 37):
            env = dict(os.environ, PATH=str(prefix / 'bin'), CLANG_AS_STATUS=str(status))
            result = subprocess.run([str(wrapper), *words], env=env, capture_output=True)
            assert result.returncode == status and not result.stderr, result
            assert json.loads(result.stdout) == ['-c', '-x', 'assembler', *words]
    compiler.unlink()
    missing = subprocess.run([str(wrapper), 'input.s'],
                             env=dict(os.environ, PATH='/usr/bin:/bin'), capture_output=True)
    assert missing.returncode != 0 and not missing.stdout
    if args.clang:
        # Explicit test input, not an installed SDK prefix or tool fallback.
        compiler.symlink_to(args.clang)
        assembly = prefix / 'input.s'
        assembly.write_text('.data\n.globl ember_clang_as_value\n'
                            'ember_clang_as_value:\n.long 0x12345678\n')
        output = prefix / 'output.o'
        result = subprocess.run([str(wrapper), str(assembly), '-o', str(output)],
                                env={'PATH': str(prefix / 'bin'), 'LC_ALL': 'C'}, capture_output=True)
        assert result.returncode == 0, result.stderr
        data = output.read_bytes()
        assert data.startswith((b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf'))
        assert b'\x78\x56\x34\x12' in data or b'\x12\x34\x56\x78' in data
print('PASS: 10 assembler argument/status cases and missing selected compiler refusal; '
      + ('real assembler object passed' if args.clang else 'no compilation requested'))
