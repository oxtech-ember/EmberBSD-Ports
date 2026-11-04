#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check phase metadata refresh preserves build state."""
import argparse
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--fragment', type=Path, required=True)
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix='makevars-refresh-') as temporary:
    root = Path(temporary)
    work = root / 'work dir'
    work.mkdir()
    cache = work / '.stage-install_makevars.mk'
    cache.write_text('_MAKEVARS_MK=defined\nUSE_BUILTIN.expat=yes\n')
    obj = work / 'object.o'
    obj.write_bytes(b'kept')
    cookie = work / '.configure_done'
    cookie.write_text('kept')
    (root / 'Makefile').write_text(
        'WRKDIR=' + str(work) + '\nRM=/bin/rm\nRUN=\n'
        '.include "' + str(args.fragment) + '"\nUSE_BUILTIN.expat?=no\n')

    def run(*arguments):
        result = subprocess.run([str(args.bmake), '-r', '-C', str(root), *arguments],
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    assert run('-V', '${USE_BUILTIN.expat}') == 'yes'
    run('invalidate-makevars')
    assert run('-V', '${USE_BUILTIN.expat}') == 'no'
    assert not cache.exists()
    assert obj.read_bytes() == b'kept'
    assert cookie.read_text() == 'kept'
print('PASS: cached variables refreshed; object and phase cookie preserved')
