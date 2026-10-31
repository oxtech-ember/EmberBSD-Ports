#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the licences that every EmberBSD build accepts."""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
# The bulk set accepts AGPL-3 (ghostscript-agpl) and the Realtek firmware licence (rtw88-firmware).
# Native QEMU on macOS needs APSL 2.0 for devel/cctools codesign_allocate.
# Native MIG (devel/mig) for the Kerberos KCM RPC stubs needs APSL 1.0 and the CMU licence.
REQUIRED = ('esdl-license', 'gnu-agpl-v3', 'rtlwifi-firmware-license',
            'apple-public-source-license', 'uboot-BSD-2-Clause-Patent',
            'uboot-BSD-3-Clause-Clear', 'uboot-LZMA-SDK-9.22', 'uboot-Intel',
            'uboot-eCos-2.0', 'uboot-bzip2-1.0.6',
            'apple-public-source-license-1.0', 'cmu-mig-license')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True, help='absolute Ports bmake executable')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        shutil.copy2(ROOT / 'pkgsrc/defaults.mk.conf', work / 'EMBERBSD-DEFAULTS-MK.CONF')
        shutil.copy2(ROOT / 'pkgsrc/versions.mk', work / 'EMBERBSD-VERSIONS.MK')
        makefile = work / 'Makefile'
        makefile.write_text('BSD_PKG_MK= yes\n.include "' + str(work / 'EMBERBSD-DEFAULTS-MK.CONF') + '"\n')
        for system, cross in (('Darwin', 'no'), ('NetBSD', 'yes')):
            result = subprocess.run([args.bmake, '-r', '-f', str(makefile), 'OPSYS=' + system,
                                     'USE_CROSS_COMPILE=' + cross, 'PKGPATH=sysutils/rtw88-firmware',
                                     '-V', '${ACCEPTABLE_LICENSES}'], capture_output=True, text=True)
            accepted = result.stdout.split()
            missing = [name for name in REQUIRED if name not in accepted]
            if result.returncode != 0 or missing:
                print('FAIL: ' + system + ' does not accept ' + ' '.join(missing) + ' ' + result.stderr.strip())
                return 1
    print('PASS: native and cross builds accept ' + ' '.join(REQUIRED))
    return 0


if __name__ == '__main__':
    sys.exit(main())
