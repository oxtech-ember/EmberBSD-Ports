#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the real gettext owner against a caller-selected archive and SDK."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'git', 'patch', 'archive', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', str(args.sdk_source), '--git', str(args.git)]
with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    root = Path(directory) / 'prepared'
    def run(*words, success=True):
        result = subprocess.run([*base, *map(str, words)], capture_output=True, text=True)
        if (result.returncode == 0) != success:
            raise AssertionError(result.stderr)
        return result
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, '--scoped-identity')
    run('verify-source', '--source', root, '--patch', args.patch)
    assert (root / 'gettext-tools/src/msgfmt.c').is_file()
    assert (root / 'gettext-tools/src/Makefile.in').is_file()
    assert 'EMBER_GETTEXT_PLAIN_STYLE' in (root / 'gettext-tools/configure.ac').read_text()
    assert 'EMBER_GETTEXT_PLAIN_STYLE' in (root / 'gettext-tools/configure').read_text()
    assert 'libgettextpo/textstyle.in.h' in (root / 'gettext-tools/src/Makefile.in').read_text()
    assert (root / 'gettext-tools/src/Makefile.am').stat().st_mtime_ns == (root / 'gettext-tools/src/Makefile.in').stat().st_mtime_ns
    for aclocal, macro in (('gettext-runtime/intl/aclocal.m4', 'gettext-runtime/m4/gettext.m4'),
                           ('gettext-tools/aclocal.m4', 'gettext-tools/gnulib-m4/gocomp.m4'),
                           ('configure', 'gettext-tools/configure.ac')):
        assert (root / macro).stat().st_mtime_ns == (root / aclocal).stat().st_mtime_ns
    runtime_macro = (root / 'gettext-runtime/m4/gettext.m4').read_text()
    runtime_configure = (root / 'gettext-runtime/configure').read_text()
    corrected = '#define __GNU_GETTEXT_SYMBOL_EXPRESSION (_nl_msg_cat_cntr)'
    assert runtime_macro.count(corrected) == 2
    assert runtime_configure.count(corrected) == 2
    intl_configure = (root / 'gettext-runtime/intl/configure').read_text()
    assert intl_configure.count(corrected) == 2
    assert (root / 'gettext-tools/configure').read_text().count(corrected) == 2
    assert (root / 'gettext-tools/configure.ac').stat().st_mtime_ns <= (root / 'gettext-tools/aclocal.m4').stat().st_mtime_ns
    assert (root / 'gettext-runtime/m4/gettext.m4').stat().st_mtime_ns <= (root / 'gettext-runtime/aclocal.m4').stat().st_mtime_ns
    assert '#define __GNU_GETTEXT_SYMBOL_EXPRESSION (_nl_msg_cat_cntr + *_nl_expand_alias (""))' not in runtime_configure
    go_macro = (root / 'gettext-tools/gnulib-m4/gocomp.m4').read_text()
    go_configure = (root / 'gettext-tools/configure').read_text()
    for line in go_macro.splitlines():
        if line.strip().startswith('gt_go_candidates='):
            assert line.strip() in go_configure
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, success=False)
    (root / 'unexpected').write_text('changed\n')
    assert 'payload changed' in run('verify-source', '--source', root, '--patch', args.patch, success=False).stderr
    (root / 'unexpected').unlink()
    run('verify-source', '--source', root, '--patch', args.patch)
print('gettext common prepared source: PASS')
