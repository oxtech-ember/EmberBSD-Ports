#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that native lang/llvm installs the llvm-min-tblgen that cross builds run."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', type=Path, required=True,
                        help='native Ports make wrapper: MAKE PKGPATH [VAR=value] TARGET|-v VARIABLE')
    parser.add_argument('--prefix', type=Path, help='also run the tool installed in this prefix')
    args = parser.parse_args()
    version = re.search(r'^LLVM_VERSION=\s*(\S+)', (ROOT / 'pkgsrc/lang/llvm/version.mk').read_text(), re.M)
    if version is None:
        print('FAIL: no LLVM_VERSION in lang/llvm/version.mk')
        return 1
    result = subprocess.run([str(args.make), 'lang/llvm', '-v', 'PLIST.min_tblgen'],
                            capture_output=True, text=True)
    if result.returncode != 0 or result.stdout.strip() != 'yes':
        print('FAIL: the native PLIST omits bin/llvm-min-tblgen: ' + (result.stdout + result.stderr).strip()[:300])
        return 1
    if '${PLIST.min_tblgen}bin/llvm-min-tblgen' not in (ROOT / 'pkgsrc/lang/llvm/PLIST').read_text().splitlines():
        print('FAIL: lang/llvm/PLIST has no bin/llvm-min-tblgen entry')
        return 1
    result = subprocess.run([str(args.make), 'lang/llvm', '-n', 'llvm-install-min-tblgen'],
                            capture_output=True, text=True)
    if result.returncode != 0 or not re.search(r'cmake-pkgsrc-build/bin/llvm-min-tblgen\S*\s+\S*/bin\b',
                                                 result.stdout):
        print('FAIL: native post-install does not install llvm-min-tblgen: '
              + (result.stdout + result.stderr).strip()[:300])
        return 1
    if args.prefix:
        tool = args.prefix / 'bin/llvm-min-tblgen'
        result = subprocess.run([str(tool), '--version'], capture_output=True, text=True)
        if result.returncode != 0 or 'LLVM version ' + version.group(1) not in result.stdout:
            print('FAIL: ' + str(tool) + ' does not report LLVM ' + version.group(1))
            return 1
    print('PASS: native lang/llvm installs llvm-min-tblgen for cross builds')
    return 0


if __name__ == '__main__':
    sys.exit(main())
