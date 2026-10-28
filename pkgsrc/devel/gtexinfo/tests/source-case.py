#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compare every regular upstream archive member with the extracted source."""
import argparse
from pathlib import Path
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive', type=Path, required=True)
p.add_argument('--source', type=Path, required=True)
a = p.parse_args()
base = 'tta/perl/t/results/init_files_tests/add_lower_case_redirection_file_names/res_html/'
relocated = {base + 'Chap.html', base + 'Up-and-Down.html'}
checked = 0
with tarfile.open(a.archive) as archive:
    for member in archive:
        if not member.isfile():
            continue
        prefix, relative = member.name.split('/', 1)
        if prefix != 'texinfo-7.3':
            raise SystemExit('unexpected archive root: ' + member.name)
        path = a.source / ('.ember-case-preserved/texinfo-7.3/' if relative in relocated else '') / relative
        expected = archive.extractfile(member).read()
        if path.read_bytes() != expected:
            raise SystemExit('archive member mismatch: ' + relative)
        checked += 1
if checked == 0:
    raise SystemExit('no archive files checked')
print('full Texinfo archive files: PASS (%d)' % checked)
