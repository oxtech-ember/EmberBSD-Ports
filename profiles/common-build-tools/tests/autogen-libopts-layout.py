#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compare libopts public structure layout with selected target tools."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('compiler', 'objcopy', 'sysroot', 'old-source', 'new-source'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--target', required=True)
args = parser.parse_args()
source = '''#include <stddef.h>
#include <autoopts/options.h>
const unsigned long layout[] = {
    sizeof(tOptions), offsetof(tOptions, pzProgPath),
    offsetof(tOptions, pzProgName), offsetof(tOptions, pzPROGNAME),
    offsetof(tOptions, pOptDesc), sizeof(tArgList), offsetof(tArgList, apzArgs)
};
'''
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    code = root / 'layout.c'
    code.write_text(source)
    outputs = []
    for index, include in enumerate((args.old_source, args.new_source)):
        obj = root / f'{index}.o'
        binary = root / f'{index}.bin'
        subprocess.run([str(args.compiler), '--target=' + args.target,
                        '--sysroot=' + str(args.sysroot), '-DHAVE_STDBOOL_H',
                        '-DHAVE_STDINT_H', '-I' + str(include), '-c', str(code),
                        '-o', str(obj)], check=True)
        subprocess.run([str(args.objcopy), '--dump-section', '.rodata=' + str(binary),
                        str(obj)], check=True)
        outputs.append(binary.read_bytes())
    if not outputs[0] or outputs[0] != outputs[1]:
        raise SystemExit('libopts public structure layout changed')
print('libopts target structure sizes and offsets: PASS')
