#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check GoogleTest's native replacement ABI floor using selected bmake."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--pkgsrc', type=Path, required=True)
parser.add_argument('--make-mk', type=Path, required=True)
args = parser.parse_args()
if not args.bmake.is_absolute() or not args.pkgsrc.is_absolute() or not args.make_mk.is_absolute():
    parser.error('absolute paths are required')
with tempfile.TemporaryDirectory(prefix='googletest-abi-floor-') as tmp:
    makefile = Path(tmp) / 'Makefile'
    makefile.write_text('BSD_PKG_MK=yes\n.include "' + str(args.pkgsrc / 'devel/googletest/buildlink3.mk') + '"\n')
    for variables, needs_nb1 in [
        (['OPSYS=Darwin', 'USE_CROSS_COMPILE=no', 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], True),
        (['OPSYS=NetBSD', 'USE_CROSS_COMPILE=yes', 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], False),
        (['OPSYS=Darwin', 'USE_CROSS_COMPILE=no'], False),
    ]:
        result = subprocess.run([str(args.bmake), '-m', str(args.make_mk), '-f', str(makefile), *variables,
                                 '-V', '${BUILDLINK_ABI_DEPENDS.googletest}'],
                                check=True, capture_output=True, text=True,
                                cwd=args.pkgsrc / 'devel/googletest')
        if ('googletest>=1.18.0nb1' in result.stdout.split()) != needs_nb1:
            raise AssertionError(result.stdout)
print('GoogleTest native and target ABI floors PASS')
