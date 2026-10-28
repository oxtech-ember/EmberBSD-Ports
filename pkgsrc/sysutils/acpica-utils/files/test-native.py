#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise packaged ACPICA namespace, resource dumps and method teardown."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--iasl', required=True)
parser.add_argument('--acpiexec', required=True)
args = parser.parse_args()
for path in (args.iasl, args.acpiexec):
    if not os.path.isabs(path) or not os.access(path, os.X_OK):
        parser.error('select executable tools by absolute path')
source = '''DefinitionBlock ("", "DSDT", 2, "EMBER", "SDKTEST", 1)
{
    Scope (\\_SB)
    {
        Name (SIZE, 0x04)
        Name (PKG0, Package (SIZE) { SIZE, SIZE })
        Device (DEV0)
        {
            Name (_HID, "PNP0501")
            Name (_PRS, ResourceTemplate () { IO (Decode16, 0x03F8, 0x03F8, 0x08, 0x08) })
            Name (_CRS, ResourceTemplate () { IO (Decode16, 0x03F8, 0x03F8, 0x08, 0x08) })
            Method (_DIS, 0, NotSerialized) { Return (Zero) }
            Method (_SRS, 1, NotSerialized) { Return (Zero) }
        }
        Alias (DEV0, DVA0)
        Method (GET0, 0, NotSerialized) { Return (0x2A) }
        Alias (GET0, MTA0)
        Method (CALL, 0, NotSerialized) { Return (MTA0 ()) }
        Name (VAL0, One)
        Name (OUT0, Zero)
        Method (NT01, 0, NotSerialized) { Return (And (LNot (Store (LNot (VAL0), OUT0)), One)) }
        Method (NT00, 0, NotSerialized)
        {
            Store (LNot (VAL0), Local0)
            Store (LNot (LNot (VAL0)), Local1)
            Store (One, Local2)
            Store (LNot (LOr (VAL0, OUT0)), Local3)
            If (LNotEqual (Local0, Zero)) { Return (0xEE) }
            If (LLessEqual (Local1, Zero)) { Return (0xED) }
            If (LGreaterEqual (Local2, 2)) { Return (0xEC) }
            Return (Add (Add (Local1, Local2), Local3))
        }
    }
}
'''
with tempfile.TemporaryDirectory(prefix='acpica-functional-', dir=os.environ.get('TMPDIR')) as temporary:
    work = Path(temporary)
    path = work / 'test.asl'
    path.write_text(source)
    build = subprocess.run([args.iasl, str(path)], cwd=work, text=True, capture_output=True, timeout=30)
    if build.returncode or '0 Errors, 0 Warnings' not in build.stdout:
        raise SystemExit('ASL compilation failed:\n' + build.stdout + build.stderr)
    run = subprocess.run([args.acpiexec, '-va', '-b', 'namespace; resources _SB.DEV0; dump _SB.DEV0; evaluate _SB.CALL; evaluate _SB.NT00; evaluate _SB.NT01',
                          str(work / 'test.aml')], cwd=work, text=True, capture_output=True, timeout=30)
    output = run.stdout + run.stderr
    for expected in ('DEV0', 'DVA0 Alias', 'MTA0 MethodAlias', 'I/O Resource', '000000000000002A', '[Integer] = 0000000000000000', '[Integer] = 0000000000000001', 'No outstanding allocations'):
        if expected not in output:
            raise SystemExit('Missing expected ' + expected + ':\n' + output)
    if run.returncode or 'ACPI Error:' in output:
        raise SystemExit('acpiexec failed:\n' + output)
    original = (work / 'test.aml').read_bytes()
    for option in ('-d', '-dl'):
        (work / 'test.aml').write_bytes(original)
        disassemble = subprocess.run([args.iasl, option, str(work / 'test.aml')], cwd=work,
                                     text=True, capture_output=True, timeout=30)
        if disassemble.returncode:
            raise SystemExit('ASL disassembly failed:\n' + disassemble.stdout + disassemble.stderr)
        dsl = (work / 'test.dsl').read_text()
        if 'Package (SIZE)' not in dsl or 'Package (SIZE, ' in dsl:
            raise SystemExit('VariablePackage size was rendered as an element:\n' + dsl)
        recompile = subprocess.run([args.iasl, str(work / 'test.dsl')], cwd=work,
                                   text=True, capture_output=True, timeout=30)
        if recompile.returncode or (work / 'test.aml').read_bytes() != original:
            raise SystemExit('ASL round trip failed:\n' + recompile.stdout + recompile.stderr)
        rerun = subprocess.run([args.acpiexec, '-b', 'evaluate _SB.NT00; evaluate _SB.NT01', str(work / 'test.aml')],
                               cwd=work, text=True, capture_output=True, timeout=30)
        if rerun.returncode or any(v not in rerun.stdout + rerun.stderr for v in ('[Integer] = 0000000000000000', '[Integer] = 0000000000000001')):
            raise SystemExit('Recompiled LNot semantics failed:\n' + rerun.stdout + rerun.stderr)
print('PASS: ASL round trip, namespace aliases, resource decoding and method teardown')
