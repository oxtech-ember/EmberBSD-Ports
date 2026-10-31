#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the selected blocklist interface is enabled only on request."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--cc', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
args = parser.parse_args()
assert args.cc.is_absolute() and args.source.is_absolute()
code = r'''
#include "pfilter.h"
static int calls;
#ifdef WITH_NETBSD_BLOCKLIST
void pfilter_notify(int event) { calls += event; }
#endif
int main(void) {
    pfilter_notify(1);
#ifdef WITH_NETBSD_BLOCKLIST
    return calls != 1;
#else
    return calls != 0;
#endif
}
'''
with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    source = Path(directory) / 'check.c'
    source.write_text(code)
    for enabled in (False, True):
        output = Path(directory) / ('enabled' if enabled else 'default')
        cmd = [str(args.cc), '-Wall', '-Wextra', '-Werror', '-I', str(args.source),
               str(source), '-o', str(output)]
        if enabled:
            cmd.insert(1, '-DWITH_NETBSD_BLOCKLIST')
        subprocess.run(cmd, check=True, env=dict(os.environ))
        subprocess.run([str(output)], check=True)
print('PASS: blocklist guard default and selected interface')
