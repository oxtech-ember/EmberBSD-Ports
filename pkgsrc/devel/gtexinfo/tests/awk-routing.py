#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check installed texindex's awk selection with real pkgsrc metadata."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'pkgsrc', 'native-config', 'cross-config'):
    parser.add_argument('--' + name, required=True)
args = parser.parse_args()
package = str(Path(args.pkgsrc) / 'devel/gtexinfo')

def query(config, *extra):
    env = dict(os.environ, MAKECONF=config)
    result = subprocess.run([args.bmake, '-C', package, *extra,
                             '-V', '${CONFIGURE_ARGS}', '-V', '${AWK}', '-V', '${REPLACE.sys-sh.new}',
                             '-V', '${SH}', '-V', '${REPLACE_SH}', '-V', '${SUBST_SED.target-hook-awk}'],
                            env=env, check=True, text=True, capture_output=True)
    flags, awk, shell, build_shell, replace_files, hook = result.stdout.splitlines()
    assert set(('util/texi2dvi', 'util/texi2pdf', 'util/pdftexi2dvi', 'texindex/texindex.in',
                'info/info-hooks-default/manual-not-found.in')) <= set(replace_files.split())
    values = [word.split('=', 1)[1] for word in shlex.split(flags)
              if word.startswith('ac_cv_path_TI_AWK=')]
    assert len(values) == 1
    return values[0], awk, shell, build_shell, hook

native, awk, shell, build_shell, hook = query(args.native_config, 'EMBERBSD_DARWIN_BOOTSTRAP=yes')
assert native == awk and shell == build_shell and not hook, (native, awk, shell, build_shell, hook)
cross, _, shell, _, hook = query(args.cross_config)
assert cross == '/usr/bin/awk' and shell == '/bin/sh' and 'AWK=/usr/bin/awk' in hook, (cross, shell, hook)
print('texindex native and NetBSD cross awk routing: PASS')
