#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the patched tests Makefile condition with selected GNU make."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'gmake', 'shell', 'work-dir'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
template = (a.source / 'gettext-tools/tests/Makefile.in').read_text()
start = template.index('ifeq ($(shell uname -s),SCO_SV)')
end = template.index('\nendif', start) + len('\nendif')
conditional = template[start:end].replace('@USE_INCLUDED_LIBINTL@', 'no').replace('@INTL_MACOSX_LIBS@', '')
with tempfile.TemporaryDirectory(dir=a.work_dir) as name:
    work = Path(name)
    makefile = work / 'Makefile'
    makefile.write_text(conditional + '\nLDADD_no = selected\nall:\n\t@print -r -- "$(LDADD)"\n')
    uname = work / 'uname'
    for value, expected in (('Darwin', 'selected'), ('SCO_SV', '')):
        uname.write_text('#!' + str(a.shell) + '\nprint -r -- ' + value + '\n')
        uname.chmod(0o755)
        result = subprocess.run([str(a.gmake), '-f', str(makefile), 'SHELL=' + str(a.shell), 'all'],
                                cwd=work, env=dict(os.environ, PATH=str(work), SHELL=str(a.shell)),
                                text=True, capture_output=True)
        if result.returncode:
            raise SystemExit(result.stderr)
        if result.stdout.strip() != expected:
            raise SystemExit('wrong GNU make LDADD selection for ' + value)
print('gettext tests GNU make conditional: PASS')
