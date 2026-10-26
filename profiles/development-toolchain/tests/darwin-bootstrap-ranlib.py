#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check that configure scripts get the selected ranlib, not Apple `ranlib -c`.

usage: darwin-bootstrap-ranlib.py EXPORTED_PKGSRC BMAKE MAKECONF WORK

OpenSSL's darwin-common target uses "ranlib -c" unless RANLIB is set in
the environment. llvm-ranlib rejects -c. The policy must pass the selected
ranlib, and that ranlib must index a common symbol without -c.
"""
import json
import shlex
import subprocess
import sys
from pathlib import Path


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    exported, bmake, makeconf, work = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    names = ['EMBERBSD_DARWIN_RANLIB', 'EMBERBSD_DARWIN_AR', 'EMBERBSD_DARWIN_NM', 'EMBERBSD_DARWIN_SEED_CC',
             'CONFIGURE_ENV']
    out = subprocess.run([bmake, '-C', str(exported / 'security/openssl'), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                          f'MAKECONF={makeconf}', 'show-vars', f'VARNAMES={" ".join(names)}'],
                         check=True, capture_output=True, text=True,
                         env={'PATH': '/usr/bin:/bin'}).stdout.splitlines()
    values = dict(zip(names, out))
    ranlib = values['EMBERBSD_DARWIN_RANLIB']
    given = [w.split('=', 1)[1] for w in shlex.split(values['CONFIGURE_ENV']) if w.startswith('RANLIB=')]
    require(given == [ranlib], f'configure scripts do not get the selected ranlib: {given!r}')
    work.mkdir(parents=True)
    (work / 'common.c').write_text('int ember_common;\n')
    subprocess.run(shlex.split(values['EMBERBSD_DARWIN_SEED_CC']) + ['-fcommon', '-c', 'common.c'],
                   cwd=work, check=True)
    subprocess.run([values['EMBERBSD_DARWIN_AR'], 'cr', 'libcommon.a', 'common.o'], cwd=work, check=True)
    apple = subprocess.run([ranlib, '-c', 'libcommon.a'], cwd=work, capture_output=True, text=True)
    require(apple.returncode != 0, 'The selected ranlib accepts -c; this policy may be stale')
    subprocess.run([ranlib, 'libcommon.a'], cwd=work, check=True)
    index = subprocess.run([values['EMBERBSD_DARWIN_NM'], '--print-armap', 'libcommon.a'], cwd=work,
                           check=True, capture_output=True, text=True).stdout
    require('_ember_common in common.o' in index, f'The archive index lacks the common symbol:\n{index}')
    print(json.dumps({'ranlib': ranlib, 'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
