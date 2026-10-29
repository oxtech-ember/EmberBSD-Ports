#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise upstream quotation catalog rules with a separate object directory."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'host-prefix', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
source = a.source / 'gettext-tools/po'
bin = a.host_prefix / 'bin'
with tempfile.TemporaryDirectory(prefix='gettext-quot-', dir=a.work_dir) as temp:
    build = Path(temp)
    (build / 'Makefile').write_text(
        'srcdir := ' + str(source) + '\n'
        'VPATH := ' + str(source) + '\n'
        'PACKAGE := ember-base-check\nCROSS_COMPILING := yes\nDOMAIN := gettext-tools\n'
        'MSGINIT := ' + str(bin / 'msginit') + '\n'
        'MSGCONV := ' + str(bin / 'msgconv') + '\n'
        'MSGFILTER := ' + str(bin / 'msgfilter') + '\n'
        'SED := ' + str(bin / 'gsed') + '\n'
        'include ' + str(source / 'Rules-quot') + '\n')
    env = dict(os.environ, PATH=str(bin) + ':' + str(a.host_prefix / 'gnu/bin'),
               TMPDIR=str(a.work_dir))
    for lang in ('en@quot', 'en@boldquot'):
        subprocess.run([str(bin / 'gmake'), 'SHELL=' + str(bin / 'mksh'), lang + '.po-create'],
                       cwd=build, env=env, check=True, capture_output=True)
        po = build / (lang + '.po')
        if not po.is_file() or (source / (lang + '.po')).exists():
            raise SystemExit('quotation PO was not generated exclusively in object directory')
        subprocess.run([str(bin / 'msgfmt'), '-o', str(build / (lang + '.gmo')), str(po)],
                       cwd=build, env=env, check=True, capture_output=True)
print('gettext quotation catalog object build: PASS')
