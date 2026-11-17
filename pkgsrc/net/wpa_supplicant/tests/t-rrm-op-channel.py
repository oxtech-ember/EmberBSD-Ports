#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run the production RRM operating-class parser against a valid and invalid frequency."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--cc', required=True)
p.add_argument('--source', required=True, help='effective prepared WPA source root')
p.add_argument('--host-sdk', required=True, help='selected native host SDK')
p.add_argument('--cflags', default='-O2 -g -Wall -Wextra -Werror -Wno-unused-parameter')
p.add_argument('--emit-c')
a = p.parse_args()
root = Path(a.source)
rrm = root / 'wpa_supplicant/rrm.c'
common = root / 'src/common/ieee802_11_common.c'
assert rrm.is_file() and common.is_file()

harness = r'''#include "includes.h"
#include "utils/common.h"
#include "common/defs.h"
#include "common/ieee802_11_common.h"
void wpa_printf(int level, const char *fmt, ...) { (void) level; (void) fmt; }
void wpa_hexdump(int level, const char *title, const void *buf, size_t len)
{ (void) level; (void) title; (void) buf; (void) len; }
int wpas_get_op_chan_phy(int freq, const u8 *ies, size_t ies_len,
                         u8 *op_class, u8 *chan, u8 *phy_type);
int main(void)
{
    /* Valid HT Operation IE: element 61, body length 22, primary channel 3,
     * secondary-channel offset 0 (HT20). */
    const u8 ht_operation[24] = { 61, 22, 3, 0 };
    u8 op_class, channel, phy;
    int ret;

    op_class = 0xaa; channel = 0xbb; phy = 0xcc;
    ret = wpas_get_op_chan_phy(2422, ht_operation, sizeof(ht_operation),
                               &op_class, &channel, &phy);
    if (ret != 0 || op_class != 81 || channel != 3 || phy != PHY_TYPE_HT) {
        fprintf(stderr, "valid channel: ret=%d op=%u chan=%u phy=%u\\n",
                ret, op_class, channel, phy);
        return 1;
    }

    op_class = 0xaa; channel = 0xbb; phy = 0xcc;
    ret = wpas_get_op_chan_phy(2423, ht_operation, sizeof(ht_operation),
                               &op_class, &channel, &phy);
    if (ret != -1 || op_class != 0xaa || channel != 0xbb || phy != 0xcc) {
        fprintf(stderr, "invalid channel: ret=%d op=%u chan=%u phy=%u\\n",
                ret, op_class, channel, phy);
        return 2;
    }
    return 0;
}
'''
if a.emit_c:
    Path(a.emit_c).write_text(harness)

with tempfile.TemporaryDirectory(prefix='wpa-rrm-op-channel-') as tmp:
    exe = Path(tmp) / 'rrm-op-channel'
    includes = [f'-I{root / "src"}', f'-I{root / "src/utils"}',
                f'-I{root / "src/common"}', f'-I{root / "src/drivers"}']
    sysroot = ['-isysroot', a.host_sdk] if sys.platform == 'darwin' else [f'--sysroot={a.host_sdk}']
    linker_gc = '-Wl,-dead_strip' if sys.platform == 'darwin' else '-Wl,--gc-sections'
    cmd = [a.cc, *sysroot, *shlex.split(a.cflags), '-ffunction-sections',
           '-fdata-sections', *includes, str(rrm), str(common), '-x', 'c', '-',
           linker_gc, '-o', str(exe)]
    compiled = subprocess.run(cmd, input=harness, text=True, capture_output=True)
    if compiled.returncode:
        raise SystemExit(compiled.stderr)
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    if run.returncode:
        raise SystemExit(run.stdout + run.stderr)
