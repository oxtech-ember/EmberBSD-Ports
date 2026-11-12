#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the native recipe and generated runtime CPU dispatch after configure."""
import argparse
import re
import shlex
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--pkgsrc', type=Path, required=True)
p.add_argument('--makeconf', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--work-source', type=Path, required=True)
a = p.parse_args()
q = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc / 'multimedia/libvpx'),
                    'MAKECONF=' + str(a.makeconf), 'USE_CROSS_COMPILE=no',
                    '-V', '${CONFIGURE_ARGS}'], check=True, capture_output=True,
                   text=True, timeout=90)
args = shlex.split(q.stdout)
assert '--target=arm64-darwin20-gcc' in args, args
assert '--enable-runtime-cpu-detect' in args, args
assert '--disable-runtime-cpu-detect' not in args, args
config = (a.work_source / 'vpx_config.h').read_text()
assert re.search(r'^#define CONFIG_RUNTIME_CPU_DETECT 1$', config, re.M), 'runtime CPU detection is disabled'
rtcd = (a.work_source / 'vpx_dsp_rtcd.h').read_text()
assert not re.search(r'^#define vpx_sum_squares_2d_i16\s+vpx_sum_squares_2d_i16_sve\s*$', rtcd, re.M), 'SVE is statically selected'
assert re.search(r'vpx_sum_squares_2d_i16.*HAS_SVE|HAS_SVE.*vpx_sum_squares_2d_i16',rtcd), 'SVE runtime dispatch missing'
print('PASS: Darwin native recipe selects runtime CPU detection and guarded SVE dispatch')
