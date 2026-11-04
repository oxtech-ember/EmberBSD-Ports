#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the actual common recipe with a selected cross MAKECONF and bmake."""
import os
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 4:
    sys.exit('usage: libepoll-cross.py BMAKE PKGSRC CROSS_MAKECONF')
make, tree, makeconf = sys.argv[1:]
base = [make, '-C', str(Path(tree) / 'devel/libepoll-shim'),
        'MAKECONF=' + makeconf]
refusal = 'requires the measured EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=0 or 1'
def check(args, expected, refused):
    result = subprocess.run(base + args + ['-V', '${EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE}',
        '-V', '${PKG_FAIL_REASON}', '-V', '${CMAKE_CONFIGURE_ARGS}'],
        text=True, capture_output=True, check=True)
    lines = result.stdout.splitlines()
    assert lines[0] == expected, result.stdout
    assert (refusal in lines[1]) == refused, result.stdout
    if not refused:
        assert '-DALLOWS_ONESHOT_TIMERS_WITH_TIMEOUT_ZERO_EXITCODE:STRING=' + expected in lines[2]
check([], '1', False)
check(['EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=0'], '0', False)
check(['EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=2'], '2', True)
check(['CROSS_OPSYS=OpenBSD'], '', True)
check(['CROSS_OS_VERSION=10.1'], '', True)
check(['CROSS_MACHINE_ARCH=riscv64'], '', True)
check(['CROSS_OPSYS=OpenBSD', 'EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=0'], '0', False)
print('PASS: recorded NetBSD 11 cross result, override, and refusals')
