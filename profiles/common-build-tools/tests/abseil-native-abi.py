#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check Abseil's native replacement ABI floor with selected bmake."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True)
    args = parser.parse_args()
    buildlink = Path(__file__).resolve().parents[3]/'pkgsrc/devel/abseil/buildlink3.mk'
    with tempfile.TemporaryDirectory(prefix='abseil-abi-floor-') as temporary:
        makefile = Path(temporary)/'Makefile'
        makefile.write_text('.include "'+str(buildlink)+'"\n')
        cases = [(['OPSYS=Darwin', 'USE_CROSS_COMPILE=no',
                   'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], True),
                 (['OPSYS=NetBSD', 'USE_CROSS_COMPILE=yes',
                   'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], False),
                 (['OPSYS=Darwin', 'USE_CROSS_COMPILE=no'], False)]
        for variables, needs_nb4 in cases:
            result = subprocess.run([args.bmake, '-f', str(makefile), *variables,
                                     '-V', '${BUILDLINK_ABI_DEPENDS.abseil}'],
                                    check=True, text=True, capture_output=True)
            floors = result.stdout.split()
            if 'abseil>=20260817.0nb3' not in floors or (
                    ('abseil>=20260817.0nb4' in floors) != needs_nb4):
                raise SystemExit('unexpected Abseil ABI floor: '+result.stdout)
    print('native and target Abseil ABI floors: PASS')


if __name__ == '__main__':
    main()
