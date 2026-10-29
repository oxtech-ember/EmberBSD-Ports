#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run ordinary NTP ntpq options against a selected native AutoGen build."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('compiler', 'linker', 'host-sysroot', 'ntp-source', 'ntp-config', 'autogen-build'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--library-path-variable', required=True,
                    choices=('DYLD_LIBRARY_PATH', 'LD_LIBRARY_PATH'))
args = parser.parse_args()
source = args.ntp_source
lib = args.autogen_build / 'autoopts' / '.libs'
program = '''#include "ntpq-opts.h"
#include <stdio.h>
void ntpOptionPrintVersion(tOptions *o, tOptDesc *d) { (void)o; (void)d; }
void ntpq_custom_opt_handler(tOptions *o, tOptDesc *d) { (void)o; (void)d; }
int main(int argc, char **argv) {
    optionProcess(&ntpqOptions, argc, argv);
    if (!HAVE_OPT(NUMERIC) || !HAVE_OPT(PEERS) || !ntpqOptions.pzProgName) return 1;
    puts("ntpq numeric and peers options selected");
    return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    harness = root / 'main.c'
    binary = root / 'ntpq-options'
    harness.write_text(program)
    command = [str(args.compiler), '-isysroot', str(args.host_sysroot),
               '--ld-path=' + str(args.linker), '-I' + str(args.ntp_config),
               '-I' + str(source / 'include'), '-I' + str(source / 'ntpq'),
               '-I' + str(args.autogen_build / 'autoopts'), '-L' + str(lib),
               str(harness), str(source / 'ntpq' / 'ntpq-opts.c'), '-lopts', '-o', str(binary)]
    subprocess.run(command, check=True)
    env = dict(os.environ, **{args.library_path_variable: str(lib)})
    result = subprocess.run([str(binary), '-n', '-p'], env=env, text=True,
                            stdout=subprocess.PIPE, check=True)
    if result.stdout != 'ntpq numeric and peers options selected\n':
        raise SystemExit('unexpected ntpq option result')
print('NTP generated options and AutoGen libopts: PASS')
