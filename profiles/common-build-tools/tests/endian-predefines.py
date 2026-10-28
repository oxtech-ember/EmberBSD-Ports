#!/usr/bin/env python3
"""Check that mk/endian.mk reads the cross target byte order."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


def endian(args, pkgsrc, extra):
    # endian.mk is included from a package directory two levels below pkgsrc.
    with tempfile.TemporaryDirectory(dir=pkgsrc) as temp:
        package = Path(temp) / 'endian'
        package.mkdir()
        (package / 'Makefile').write_text('.include "../../mk/endian.mk"\n', encoding='utf-8')
        result = subprocess.run([args.bmake, 'MAKECONF=' + args.makeconf] + extra
                                + ['-v', 'MACHINE_ENDIAN'], cwd=package,
                                capture_output=True, text=True, check=True)
    # The old probe includes the build-host header path and clang reports it.
    error = 'file not found' in result.stderr
    return result.stdout.strip() + (' (header not found)' if error else '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True, help='bmake with the host mk files')
    parser.add_argument('--makeconf', required=True, help='cross MAKECONF for aarch64')
    parser.add_argument('--pkgsrc', required=True, help='exported pkgsrc tree')
    parser.add_argument('--clang', required=True, help='build-host clang with the NetBSD targets')
    parser.add_argument('--amd64-sysroot', required=True, help='amd64 sysroot')
    args = parser.parse_args()
    pkgsrc = Path(args.pkgsrc).resolve(strict=True)
    sysroot = 'TOOLS_CROSS_DESTDIR=' + args.amd64_sysroot
    cases = (
        ('aarch64', [], 'little'),
        ('amd64', ['CCPATH=' + args.clang + ' --target=x86_64--netbsd', sysroot], 'little'),
        # The old header fallback reports little for every target without _BIG_ENDIAN.
        ('aarch64_be', ['CCPATH=' + args.clang + ' --target=aarch64_be--netbsd'], 'big'),
    )
    failed = []
    for arch, extra, expected in cases:
        value = endian(args, pkgsrc, extra)
        print(arch + ': MACHINE_ENDIAN=' + value)
        if value != expected:
            failed.append(arch)
    if failed:
        print('FAIL: wrong MACHINE_ENDIAN for ' + ' '.join(failed))
        return 1
    print('PASS: MACHINE_ENDIAN comes from the target compiler')
    return 0


if __name__ == '__main__':
    sys.exit(main())
