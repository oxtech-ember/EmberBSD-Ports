#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the direct MakeMaker target prepares its selected target Config."""
import argparse
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--package', type=Path, required=True)
p.add_argument('--work-root', type=Path, required=True)
a = p.parse_args()
assert all(x.is_absolute() for x in (a.bmake, a.package, a.work_root))
commands = subprocess.check_output([str(a.bmake), '-n', '-C', str(a.package),
    'WRKOBJDIR=' + str(a.work_root), 'perl5-configure'], text=True)
assert 'prepare-build-config.py' in commands
assert 'Makefile.PL' in commands
assert commands.index('prepare-build-config.py') < commands.index('Makefile.PL')
print('Direct Perl module configure context: PASS')
