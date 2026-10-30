#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the libhfs C compiler wrapper preprocesses without diagnostics.

The bundled Autoconf 2.13 configure accepts "$CC -E" only when it prints
nothing on stderr. Link flags given to every compiler run make Clang warn,
so configure falls back to /lib/cpp and every header check fails.
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
                        help='Ports make command that takes PKGPATH and then bmake arguments')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='libhfs-cpp-') as temporary:
        work = Path(temporary).resolve()
        make = [args.make, 'devel/libhfs', 'WRKOBJDIR=' + str(work)]
        proc = subprocess.run([*make, 'wrapper'], capture_output=True, text=True)
        if proc.returncode:
            sys.exit('wrapper failed:\n' + (proc.stdout + proc.stderr)[-3000:])
        wrkdir = subprocess.run([*make, '-V', '${WRKDIR}'], capture_output=True, text=True,
                                check=True).stdout.strip()
        source = work / 'conftest.c'
        source.write_text('#include <assert.h>\n')
        cc = Path(wrkdir) / '.cwrapper/bin/cc'
        env = dict(os.environ, CWRAPPERS_CONFIG_DIR=str(Path(wrkdir) / '.cwrapper/config'))
        proc = subprocess.run([str(cc), '-E', '-I.', str(source)], cwd=work, env=env,
                              capture_output=True, text=True)
        if proc.returncode or proc.stderr.strip():
            print('FAIL: cc -E status %d, stderr: %s' % (proc.returncode, proc.stderr.strip()))
            return 1
    print('PASS: libhfs cc -E prints no diagnostics')
    return 0


if __name__ == '__main__':
    sys.exit(main())
