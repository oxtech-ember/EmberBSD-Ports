#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Evaluate native and target BSDinstall compiler bindings in the real export."""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'makefiles', 'pkgsrc', 'native-makeconf', 'cross-makeconf', 'host-prefix'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
env = dict(os.environ, PATH=a.host_prefix + '/bin:' + a.host_prefix + '/gnu/bin')
def query(makeconf, role):
    cmd = [a.bmake, '-m', a.makefiles, '-C', str(Path(a.pkgsrc) / 'sysutils/bsdinstall'),
           'MAKECONF=' + makeconf, 'USE_CROSS_COMPILE=' + role]
    if role == 'no':
        cmd.append('EMBERBSD_DARWIN_BOOTSTRAP=yes')
    cmd += ['-V', '${CPPFLAGS}', '-V', '${TOOLS_PLATFORM.strip}', '-V', '${TOOLS_PLATFORM.sh}']
    output = subprocess.run(cmd, env=env, text=True, capture_output=True, check=True).stdout.splitlines()
    return output[0], output[1], output[2]
native, strip, shell = query(a.native_makeconf, 'no')
assert '@executable_path/../bin/' + Path(strip).name in native, native
assert '@executable_path/../bin/' + Path(shell).name in native, native
target, _, _ = query(a.cross_makeconf, 'yes')
assert 'TARGET_STRIP=' not in target and 'EMBERBSD_BSDINSTALL_SHELL=' not in target
assert '@executable_path' not in target and a.host_prefix not in target
print('BSDinstall selected native and target recipe flags PASS')
