#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
"""Exercise ordinary Oncore command choices without a receiver or device IO."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for n in ('source', 'cc', 'ld', 'host-sdk', 'work-dir'):
    p.add_argument('--' + n, type=Path, required=True)
a = p.parse_args()
assert all(getattr(a, n).is_absolute() for n in vars(a))
source = (a.source / 'ntpd/refclock_oncore.c').read_text()
def function(name):
    start = source.index('\nstatic void\n' + name + '(')
    opening = source.index('{', start)
    depth = 0
    for i in range(opening, len(source)):
        if source[i] == '{': depth += 1
        if source[i] == '}': depth -= 1
        if depth == 0: return source[start:i+1]
    raise ValueError('unterminated function')
code = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct instance { int Bj_day, saw_Gj, count4, chan, traim_in, traim_id, traim_ck, traim; unsigned char BEHa[6]; };
static unsigned char oncore_cmd_Bl[]="Bl", oncore_cmd_Bj[]="Bj", oncore_cmd_Gj[]="Gj";
static unsigned char oncore_cmd_Bnx[]="Bn", oncore_cmd_Enx[]="En", oncore_cmd_Ge0[]="Ge", oncore_cmd_Hn0[]="Hn";
static char calls[32];
static void oncore_sendmsg(struct instance *i, unsigned char *cmd, size_t len) {
    (void)i; (void)len; strncat(calls, (char *)cmd, 2);
}
#define LOG_INFO 0
#define oncore_log_f(...) ((void)0)
''' + function('oncore_check_leap_sec') + function('oncore_set_traim') + r'''
int main(void) {
    const int months[] = {1, 6, 12};
    const int chans[] = {6, 8, 12};
    const char *expect[] = {"BnHn", "EnHn", "GeHn"};
    for (int j=0; j<3; j++) {
        struct instance i = {0}; i.saw_Gj = -1; i.BEHa[4] = months[j]; i.BEHa[5] = 1;
        calls[0] = 0; oncore_check_leap_sec(&i);
        assert(strcmp(calls, j == 0 ? "Bl" : "BjBl") == 0);
    }
    for (int j=0; j<3; j++) {
        struct instance i = {0}; i.chan = chans[j]; i.traim_in=0; i.traim_ck=1;
        calls[0] = 0; oncore_set_traim(&i); assert(strcmp(calls, expect[j]) == 0);
        i.traim_in=1; calls[0] = 0; oncore_set_traim(&i); assert(calls[0] == 0);
    }
    puts("Oncore ordinary command sequence: PASS");
}
'''
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    root = Path(tmp); c = root / 'test.c'; c.write_text(code)
    exe = root / 'test'
    subprocess.run([str(a.cc), '--ld-path=' + str(a.ld), '--sysroot=' + str(a.host_sdk),
                    '-std=c11', '-Wall', '-Wextra', '-Werror', str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
