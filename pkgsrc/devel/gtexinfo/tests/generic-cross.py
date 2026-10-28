#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check generic cross does not require the SDK native-role provider."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
a = p.parse_args()
assert a.bmake.is_absolute()
cross = Path(__file__).resolve().parents[1] / 'cross.mk'
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    makefile = Path(tmp) / 'Makefile'
    makefile.write_text('USE_CROSS_COMPILE=yes\n'
        'NATIVE_MACHINE_GNU_PLATFORM=host\nMACHINE_GNU_PLATFORM=target\n'
        'NATIVE_CC=/selected/cc\nNATIVE_AR=/selected/ar\n'
        'NATIVE_RANLIB=/selected/ranlib\n.include "' + str(cross) + '"\n')
    result = subprocess.check_output([str(a.bmake), '-r', '-f', str(makefile),
                                      '-V', '${CONFIGURE_ENV}'], text=True)
    assert 'BUILD_CC=/selected/cc' in result
    assert 'PATH_FOR_BUILD' not in result and 'PERL_EXT_CC_FOR_BUILD' not in result
print('Texinfo generic cross selection: PASS')
