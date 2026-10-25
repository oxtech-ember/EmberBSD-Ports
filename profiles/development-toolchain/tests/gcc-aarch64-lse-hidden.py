#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted regression for gcc-aarch64-lse-hidden.patch.
"""Check that the AArch64 LSE outline-atomic helpers stay hidden on ELF.

  gcc-aarch64-lse-hidden.py --source PATCHED_GCC_SOURCE
  gcc-aarch64-lse-hidden.py --libgcc LIBGCC_A --readelf READELF
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ENTRY = re.compile(r'^ENTRY \((ASMNAME \(NAME ?\(\w+\)\))\)$')
HELPER = re.compile(r'__aarch64_(cas(1|2|4|8|16)|(swp|ldadd|ldclr|ldeor|ldset)(1|2|4|8))'
                    r'_(relax|acq|rel|acq_rel|sync)')
# cas has 5 sizes, swp and the 4 load operations have 4; each has 5 models.
HELPERS = (5 + 5 * 4) * 4 + 5 * 5


def check_source(source):
    """Each helper ENTRY in lse.S must be preceded by an ELF-only HIDDEN."""
    lines = (Path(source) / 'libgcc/config/aarch64/lse.S').read_text().split('\n')
    entries = [(number, match[1]) for number, line in enumerate(lines)
               if (match := ENTRY.match(line))]
    if len(entries) != 3:
        raise SystemExit(f'Expected the cas, swp and ldop ENTRY lines in lse.S, found {len(entries)}')
    for number, name in entries:
        if lines[number - 3:number] != ['#ifdef __ELF__', f'\tHIDDEN ({name})', '#endif']:
            raise SystemExit(f'lse.S line {number + 1}: {name} has no ELF HIDDEN')
    print('PASS lse.S hides the cas, swp and ldop helpers on ELF', flush=True)


def check_libgcc(libgcc, readelf):
    """Every defined LSE helper in an ELF libgcc.a must have hidden visibility."""
    output = subprocess.run([readelf, '-sW', libgcc], check=True, capture_output=True, text=True).stdout
    found = {}
    for line in output.split('\n'):
        fields = line.split()
        if len(fields) == 8 and HELPER.fullmatch(fields[7]) and fields[6] != 'UND':
            if fields[7] in found:
                raise SystemExit(f'Duplicate definition of {fields[7]}')
            found[fields[7]] = fields[5]
    visible = sorted(name for name, visibility in found.items() if visibility != 'HIDDEN')
    if len(found) != HELPERS:
        raise SystemExit(f'Expected {HELPERS} LSE helpers in {libgcc}, found {len(found)}')
    if visible:
        raise SystemExit(f'{len(visible)} LSE helpers are not hidden, for example {visible[0]}')
    print(f'PASS {HELPERS} LSE helpers in libgcc.a are hidden', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source')
    parser.add_argument('--libgcc')
    parser.add_argument('--readelf')
    args = parser.parse_args()
    if bool(args.libgcc) != bool(args.readelf) or not (args.source or args.libgcc):
        parser.error('use --source DIR, or --libgcc LIBGCC_A --readelf READELF')
    if args.source:
        check_source(args.source)
    if args.libgcc:
        check_libgcc(args.libgcc, args.readelf)


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
