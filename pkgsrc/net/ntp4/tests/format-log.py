#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise ordinary NTP formatted logging with a selected native compiler."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('compiler', 'linker', 'host-sysroot', 'source', 'config'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
source = args.source
harness = '''#include "config.h"
#include <sys/time.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "ntp_stdlib.h"
int main(void) {
    char actual[512], expected[512];
    errno = ENOENT;
    int n = msnprintf(actual, sizeof(actual), FORMAT, 42, VALUE);
    int m = snprintf(expected, sizeof(expected), "item %d: %s", 42, VALUE);
    return n != m || strcmp(actual, expected) != 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for native in (False, True):
        text = harness.replace('FORMAT', '"item %d: %s"' if native else '"item %d: %m"')
        text = text.replace(', 42, VALUE);', ', 42);', 1) if not native else text.replace('VALUE', '"ok"')
        if not native:
            text = text.replace('VALUE', 'strerror(ENOENT)')
        code = root / ('native.c' if native else 'replacement.c')
        binary = root / ('native' if native else 'replacement')
        code.write_text(text)
        command = [str(args.compiler), '-isysroot', str(args.host_sysroot),
                   '--ld-path=' + str(args.linker), '-ffunction-sections', '-fdata-sections',
                   '-Wl,-dead_strip', '-DHAVE_CONFIG_H']
        if native:
            command.append('-DVSNPRINTF_PERCENT_M')
        for directory in (args.config, source / 'include', source / 'libntp/lib/isc/include',
                          source / 'libntp/lib/isc/unix/include', source / 'libntp/lib/isc/nothreads/include'):
            command.append('-I' + str(directory))
        command += [str(code), str(source / 'libntp/msyslog.c'), '-o', str(binary)]
        subprocess.run(command, check=True)
        subprocess.run([str(binary)], check=True)
print('ordinary formatted logging, both configuration branches: PASS')
