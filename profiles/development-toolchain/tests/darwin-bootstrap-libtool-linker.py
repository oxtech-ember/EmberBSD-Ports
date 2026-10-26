#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check that libtool does not take the selected ld64.lld for GNU ld.

usage: darwin-bootstrap-libtool-linker.py EXPORTED_PKGSRC BMAKE MAKECONF

libtool classifies the linker with `$LD -v`: output containing "GNU" means
GNU ld. ld64.lld prints "compatible with GNU linkers", so without a cached
answer configure scripts such as libffi's add --version-script, which the
Mach-O driver rejects. The policy must supply the cached answer "no".
"""
import json
import shlex
import subprocess
import sys
from pathlib import Path

CACHE = ['lt_cv_prog_gnu_ld', 'lt_cv_prog_gnu_ldcxx']


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    exported, bmake, makeconf = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    names = ['EMBERBSD_DARWIN_SEED_CC', 'CONFIGURE_ENV']
    out = subprocess.run([bmake, '-C', str(exported / 'devel/libffi'), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                          f'MAKECONF={makeconf}', 'show-vars', f'VARNAMES={" ".join(names)}'],
                         check=True, capture_output=True, text=True,
                         env={'PATH': '/usr/bin:/bin'}).stdout.splitlines()
    values = dict(zip(names, out))
    # libtool.m4 finds LD with `$CC -print-prog-name=ld` (_LT_PATH_LD) and
    # classifies it from `$LD -v` (_LT_PATH_LD_GNU).
    linker = subprocess.run(shlex.split(values['EMBERBSD_DARWIN_SEED_CC']) + ['-print-prog-name=ld'], check=True,
                            capture_output=True, text=True).stdout.strip()
    probe = subprocess.run([linker, '-v'], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    banner = (probe.stdout + probe.stderr).strip().splitlines()[0]
    require('LLD' in banner, f'Selected linker is not ld64.lld: {linker} {banner!r}')
    words = shlex.split(values['CONFIGURE_ENV'])
    for name in CACHE:
        given = [w.split('=', 1)[1] for w in words if w.startswith(name + '=')]
        if 'GNU' in banner or 'with BFD' in banner:
            require(given == ['no'], f'libtool takes {banner!r} for GNU ld; {name} is {given!r}')
    print(json.dumps({'linker_banner': banner, 'cached': CACHE, 'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
