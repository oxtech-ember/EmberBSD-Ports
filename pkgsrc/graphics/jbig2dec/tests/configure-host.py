#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that jbig2dec runs configure once, with the pkgsrc arguments.

autogen.sh ends by running ./configure itself, with no arguments unless it
is given some. Run from pre-configure, that bare configure has no --host and
no --prefix, so a cross build stops with "cannot run C compiled programs"
before the pkgsrc configure step starts. The recipe must regenerate the
build files only and leave configure to the do-configure step.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', required=True,
                        help='Ports make command that takes PKGPATH and then bmake arguments')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='jbig2dec-cfg-') as temporary:
        work = Path(temporary).resolve()
        make = [args.make, 'graphics/jbig2dec', 'WRKOBJDIR=' + str(work)]
        wrksrc = subprocess.run([*make, '-V', '${WRKSRC}'], capture_output=True, text=True,
                                check=True).stdout.strip()
        proc = subprocess.run([*make, 'configure'], capture_output=True, text=True)
        output = proc.stdout + proc.stderr
        runs = output.count('checking whether the C compiler works')
        log = Path(wrksrc) / 'config.log'
        invocation = ''
        if log.exists():
            for line in log.read_text(errors='replace').splitlines():
                if line.startswith('  $ '):
                    invocation = line
                    break
        if proc.returncode or runs != 1 or '--prefix=' not in invocation:
            print('FAIL: configure status %d, configure runs %d, invocation %r'
                  % (proc.returncode, runs, invocation))
            print(output[-2000:])
            return 1
    print('PASS: jbig2dec configure ran once: %s' % invocation.strip())
    return 0


if __name__ == '__main__':
    sys.exit(main())
