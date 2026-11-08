#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the polkit PAM policy includes only policies the target has.

OpenPAM fails pam_start with PAM_SYSTEM_ERR when an included policy does
not exist. polkit-agent-helper-1 then refuses every authentication.
--pam-file is the built share/examples/pam.d/polkit-1.
--pam-dir is the target's /etc/pam.d. Use an installed system, or the OS
source etc/pam.d, where templated policies end in ".in".
"""
import argparse
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('--pam-file', type=Path, required=True)
p.add_argument('--pam-dir', type=Path, required=True)
a = p.parse_args()

if not a.pam_dir.is_dir():
    print(f'FAIL: {a.pam_dir} is not a directory')
    sys.exit(1)

includes = []
for line in a.pam_file.read_text().splitlines():
    fields = line.split()
    if len(fields) >= 3 and not fields[0].startswith('#') and fields[1] == 'include':
        includes.append(fields[2])

if not includes:
    print(f'FAIL: {a.pam_file} has no include lines')
    sys.exit(1)

def present(name):
    return (a.pam_dir / name).is_file() or (a.pam_dir / (name + '.in')).is_file()


missing = sorted({name for name in includes if not present(name)})
if missing:
    print(f'FAIL: {a.pam_file} includes policies absent from {a.pam_dir}: {", ".join(missing)}')
    sys.exit(1)
print(f'OK: {a.pam_file} includes {", ".join(sorted(set(includes)))} from {a.pam_dir}')
