#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile Chromium's XNNPACK hardware configuration against selected CPUINFO headers."""
import argparse
import re
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ('xnnpack', 'pthreadpool', 'host-include', 'target-include', 'host-cc', 'target-cc', 'sysroot'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--host-cpu', choices=('arm64', 'x64'), required=True)
p.add_argument('--target-cpu', choices=('arm64', 'x64'), required=True)
a = p.parse_args()
xnn = a.xnnpack.resolve(strict=True)
flags = dict(re.findall(r'"(XNN_[A-Z0-9_]+)=(\d+)"', (xnn / 'build_defs.gni').read_text()))
flags.update(XNN_LOG_LEVEL='0', XNN_ENABLE_CPUINFO='1')
for role, cc, include in (('host', a.host_cc, a.host_include), ('target', a.target_cc, a.target_include)):
    values = dict(flags)
    cpu = a.host_cpu if role == 'host' else a.target_cpu
    for key in ('XNN_ENABLE_ARM_DOTPROD', 'XNN_ENABLE_ARM_I8MM', 'XNN_ENABLE_ASSEMBLY'):
        values[key] = '1' if cpu == 'arm64' else '0'
    values['XNN_ENABLE_AVXVNNI'] = '1' if cpu == 'x64' else '0'
    source = xnn / 'src'
    args = [str(cc.resolve(strict=True)), '-std=c11', '-fsyntax-only', '-DCHROMIUM=1']
    if role == 'target':
        args.append('--sysroot=' + str(a.sysroot.resolve(strict=True)))
    args += ['-D' + key + '=' + value for key, value in sorted(values.items())]
    args += ['-I' + str(include.resolve(strict=True)), '-I' + str(source),
             '-I' + str(source / 'include'), '-I' + str(a.pthreadpool.resolve(strict=True)),
             str(source / 'src/configs/hardware-config.c')]
    subprocess.run(args, check=True)
    print(role, 'XNNPACK hardware config CPUINFO API: PASS')
