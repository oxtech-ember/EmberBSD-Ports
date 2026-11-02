#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check Boost header and package metadata.
import os
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 4:
    raise SystemExit('Usage: boost-metadata.py PKGSRC NATIVE_MAKECONF CROSS_MAKECONF')
root, native, cross = sys.argv[1:]
bmake = os.environ['BMAKE']
for config, cross_compile in ((native, 'no'), (cross, 'yes')):
    cmd = [bmake, '-C', str(Path(root) / 'devel/boost-libs'),
           '_MAKEVARS_MK=defined', '_PKGSRC_BARRIER=yes',
           'USE_CROSS_COMPILE=' + cross_compile]
    result = subprocess.run(cmd + ['-V', '${PKGNAME}', '-V', '${BUILDLINK_API_DEPENDS.boost-headers}',
                                  '-V', '${CONFLICTS}', '-V', '${BUILDLINK_DEPMETHOD.boost-headers}',
                                  '-V', '${BUILD_DEPENDS}'],
                            env=dict(os.environ, MAKECONF=config), text=True,
                            capture_output=True, check=True)
    name, patterns, conflicts, method, build_depends = result.stdout.splitlines()
    assert name == 'boost-libs-1.92.0nb4', name
    assert patterns.split() == ['boost-headers>=1.92.0nb2<1.93'], patterns
    header_deps = [item for item in build_depends.split() if item.startswith('boost-headers') ]
    assert header_deps == ['boost-headers>=1.92.0nb2<1.93:../../devel/boost-headers'], header_deps
    assert 'boost-headers<1.92.0nb2' in conflicts.split(), conflicts
    assert method == 'build', method
    print(f'cross={cross_compile}: {name}; headers={patterns}; conflicts={conflicts}; method={method}')
print('PASS: Boost header metadata')
