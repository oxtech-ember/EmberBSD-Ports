#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check Store expression grouping through iASL and real AML execution."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--iasl', required=True)
parser.add_argument('--acpiexec', required=True)
parser.add_argument('--case', action='append', help='limit to a named case')
args = parser.parse_args()
for tool in (args.iasl, args.acpiexec):
    if not os.path.isabs(tool) or not os.access(tool, os.X_OK):
        parser.error('select executable tools by absolute path')

expressions = {name: f'{name} (Store (Arg0, OUT0), One)' for name in (
    'Add', 'Subtract', 'Multiply', 'Divide', 'Mod', 'And', 'Or', 'Xor', 'ShiftLeft',
    'ShiftRight', 'LAnd', 'LOr', 'LEqual', 'LGreater', 'LLess',
    'LNotEqual', 'LLessEqual', 'LGreaterEqual')}
expressions.update({'LNot': 'LNot (Store (Arg0, OUT0))',
                    'Not': 'Not (Store (Arg0, OUT0))',
                    'nested': 'Store (Store (Arg0, OUT0), OUT1)',
                    'statement': None,
                    'Index': 'DerefOf (Index (Store (BUF0, OUT0), One))'})

with tempfile.TemporaryDirectory(prefix='acpica-store-', dir=os.environ.get('TMPDIR')) as temporary:
    work = Path(temporary)
    def run(argv):
        result = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise SystemExit(f'failed {argv}:\n{result.stdout}{result.stderr}')
        return result.stdout + result.stderr
    def evaluate(aml, value):
        text = run([args.acpiexec, '-b', f'evaluate TST0 {value}; evaluate GET0; evaluate GET1', str(aml)])
        values = re.findall(r'\[Integer\] = ([0-9A-Fa-f]+)', text)
        if len(values) != 3 or 'ACPI Error:' in text:
            raise SystemExit('unexpected acpiexec result:\n' + text)
        return values
    if args.case and any(name not in expressions for name in args.case):
        parser.error('unknown Store test case')
    for name, expression in expressions.items():
        if args.case and name not in args.case:
            continue
        body = 'Store (Arg0, OUT0)\n        Return (OUT0)' if expression is None else f'Return ({expression})'
        source = '''DefinitionBlock ("", "DSDT", 2, "EMBER", "STORTEST", 1)
{
    Name (OUT0, One)
    Name (OUT1, One)
    Method (TST0, 1, NotSerialized)
    {
        %s
    }
    Method (GET0, 0, NotSerialized) { Return (OUT0) }
    Method (GET1, 0, NotSerialized) { Return (OUT1) }
}
''' % body
        if name == 'Index':
            source = source.replace('Name (OUT0, One)',
                'Name (BUF0, Buffer (2) { 0x12, 0x34 })\n    Name (OUT0, Buffer (2) { 0x00, 0x00 })')
            source = source.replace('Return (OUT0) }', 'Return (DerefOf (Index (OUT0, One))) }')
        (work / 'case.asl').write_text(source)
        run([args.iasl, '-oa', '-oE', 'case.asl'])
        original = (work / 'case.aml').read_bytes()
        expected = {value: evaluate(work / 'case.aml', value) for value in ('0', '2', '0xFFFFFFFFFFFFFFFF')}
        for value, result in expected.items():
            if name == 'Index':
                if [int(result[0], 16), int(result[1], 16)] != [0x34, 0x34]:
                    raise SystemExit('Index did not return and store the expected buffer element')
            else:
                if int(result[1], 16) != int(value, 0):
                    raise SystemExit(f'{name}: Store did not write OUT0 for {value}')
                if name == 'nested' and int(result[2], 16) != int(value, 0):
                    raise SystemExit(f'{name}: nested Store did not write OUT1 for {value}')
        for mode in (('-d',), ('-od', '-d'), ('-dl',)):
            (work / 'case.aml').write_bytes(original)
            run([args.iasl, *mode, 'case.aml'])
            run([args.iasl, '-oa', '-oE', 'case.dsl'])
            rebuilt = (work / 'case.aml').read_bytes()
            if rebuilt != original:
                raise SystemExit(f'{name} {mode}: AML bytes changed')
            for value, result in expected.items():
                if evaluate(work / 'case.aml', value) != result:
                    raise SystemExit(f'{name} {mode}: values or Store side effects changed for {value}')
        print(f'PASS: {name}')
print('PASS: Store byte and execution round trips, default/-od/legacy')
