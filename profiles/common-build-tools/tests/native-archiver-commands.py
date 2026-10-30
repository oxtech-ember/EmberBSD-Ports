#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a native recipe finds ar, ranlib and nm by name.

The Ports host prefix installs llvm-ar, llvm-ranlib and llvm-nm only.
Upstream configure scripts and Makefiles call ar, ranlib and nm, so a native
dependency such as devel/gperf ran "ar cr libgp.a ..." and stopped with
"ar: not found", and Autoconf chose AR=false. The native include must create
the commands in the package tools directory. RECIPE must not list ar in
USE_TOOLS.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', required=True,
                        help='make command for native recursion that takes PKGPATH and then bmake arguments')
    parser.add_argument('--recipe', default='devel/gperf')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='native-ar-') as temporary:
        work = Path(temporary).resolve()
        make = [args.make, args.recipe, 'WRKOBJDIR=' + str(work)]
        query = subprocess.run([*make, '-V', '${TOOLS_DIR}', '-V', '${USE_TOOLS:Mar}'],
                               capture_output=True, text=True, check=True).stdout.splitlines()
        tools_dir, listed = Path(query[0]), query[1:] and query[1]
        if listed:
            sys.exit('%s lists ar in USE_TOOLS; choose another recipe' % args.recipe)
        proc = subprocess.run([*make, 'tools'], capture_output=True, text=True)
        if proc.returncode:
            sys.exit('tools failed:\n' + (proc.stdout + proc.stderr)[-3000:])
        env = dict(os.environ, PATH=str(tools_dir / 'bin'))
        member = work / 'member.txt'
        member.write_text('member\n')
        failures = []
        for argv in (['ar', 'cr', 'libprobe.a', member.name], ['ranlib', 'libprobe.a'],
                     ['ar', 't', 'libprobe.a'], ['nm', '--version']):
            try:
                run = subprocess.run(argv, cwd=work, env=env, capture_output=True, text=True)
            except FileNotFoundError:
                failures.append('%s: not found in %s' % (argv[0], tools_dir / 'bin'))
                continue
            if run.returncode:
                failures.append('%s: status %d %s' % (' '.join(argv), run.returncode, run.stderr.strip()))
            elif argv[:2] == ['ar', 't'] and run.stdout.split() != [member.name]:
                failures.append('ar t listed %r' % run.stdout)
        if failures:
            print('FAIL: ' + '; '.join(failures))
            return 1
    print('PASS: native %s runs ar, ranlib and nm by name' % args.recipe)
    return 0


if __name__ == '__main__':
    sys.exit(main())
