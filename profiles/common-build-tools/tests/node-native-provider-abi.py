#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check native runtime ABI floors for Node's shared providers."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--pkgsrc-root', required=True, type=Path)
    args = parser.parse_args()
    providers = [('textproc', 'fmtlib', '12.2.0nb1'),
                 ('devel', 'spdlog', '1.17.0nb2'),
                 ('devel', 'merve', '1.2.2nb1'),
                 ('devel', 'nbytes', '0.1.4nb2'),
                 ('devel', 'lief', '1.0.0nb2')]
    cases = [(['OPSYS=Darwin', 'USE_CROSS_COMPILE=no',
               'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], True),
             (['OPSYS=NetBSD', 'USE_CROSS_COMPILE=yes',
               'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], False),
             (['OPSYS=Darwin', 'USE_CROSS_COMPILE=no'], False)]
    with tempfile.TemporaryDirectory(prefix='node-provider-abi-') as temporary:
        makefile = Path(temporary) / 'Makefile'
        for category, provider, version in providers:
            buildlink = args.pkgsrc_root / category / provider / 'buildlink3.mk'
            makefile.write_text('BSD_PKG_MK=yes\n.include "' + str(buildlink) + '"\n')
            for variables, expected in cases:
                result = subprocess.run([args.bmake, '-f', str(makefile), *variables,
                                         '-V', '${BUILDLINK_ABI_DEPENDS.' + provider + '}'],
                                        check=True, text=True, capture_output=True)
                if (provider + '>=' + version in result.stdout.split()) != expected:
                    raise SystemExit('unexpected ABI floor: ' + result.stdout)
    print('Node provider native and target ABI floors: PASS')


if __name__ == '__main__':
    main()
