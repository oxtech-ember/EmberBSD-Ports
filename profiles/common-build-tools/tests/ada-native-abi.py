#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check selected Ada provider native and cross ABI floors."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--pkgsrc-root', required=True, type=Path)
    args = parser.parse_args()
    providers = {'ada-idna': '0.7.0', 'ada-url': '4.0.0'}
    cases = [(['OPSYS=Darwin', 'USE_CROSS_COMPILE=no',
               'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], True),
             (['OPSYS=NetBSD', 'USE_CROSS_COMPILE=yes',
               'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], False),
             (['OPSYS=Darwin', 'USE_CROSS_COMPILE=no'], False)]
    with tempfile.TemporaryDirectory(prefix='ada-abi-floor-') as temporary:
        makefile = Path(temporary)/'Makefile'
        for provider, version in providers.items():
            buildlink = args.pkgsrc_root/'devel'/provider/'buildlink3.mk'
            makefile.write_text('BSD_PKG_MK=yes\n.include "'+str(buildlink)+'"\n')
            for variables, needs_nb1 in cases:
                result = subprocess.run([args.bmake, '-f', str(makefile), *variables,
                                         '-V', '${BUILDLINK_ABI_DEPENDS.'+provider+'}'],
                                        check=True, text=True, capture_output=True)
                floor = provider+'>='+version+'nb1'
                if (floor in result.stdout.split()) != needs_nb1:
                    raise SystemExit('unexpected ABI floor: '+result.stdout)
    print('native and target Ada ABI floors: PASS')


if __name__ == '__main__':
    main()
