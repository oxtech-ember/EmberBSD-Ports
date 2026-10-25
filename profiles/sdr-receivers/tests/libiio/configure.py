#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the real receiver configuration, including missing USB refusal."""
import os
from pathlib import Path
import subprocess
import sys
source, work = map(Path, sys.argv[1:3])
cache = Path(__file__).resolve().parents[4] / 'pkgsrc/devel/libiio/files/receiver.cmake'
work.mkdir()
base = [os.environ['CMAKE'], '-S', str(source), '-G', 'Ninja',
        '-DCMAKE_MAKE_PROGRAM=' + os.environ['NINJA'], '-C', str(cache),
        '-DCMAKE_C_COMPILER=' + os.environ['CC'],
        '-DCMAKE_DISABLE_FIND_PACKAGE_PkgConfig=ON',
        '-DCMAKE_FIND_USE_CMAKE_SYSTEM_PATH=OFF', '-DCMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH=OFF',
        '-DCMAKE_AR=/usr/bin/ar', '-DCMAKE_RANLIB=/usr/bin/ranlib']
p = subprocess.run(base + ['-B', str(work / 'missing-usb')], text=True, capture_output=True)
(work / 'missing-usb.log').write_text(p.stdout + p.stderr)
if p.returncode == 0 or 'Unable to find libusb-1.0 dependency' not in p.stdout + p.stderr:
    raise SystemExit('FAIL: selected receiver configuration must reject absent libusb')
print('PASS receiver configuration rejects missing USB dependency')
