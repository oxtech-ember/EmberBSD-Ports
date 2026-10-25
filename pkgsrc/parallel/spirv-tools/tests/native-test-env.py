#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check preinstall test paths with actual pkgsrc platform discovery."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bmake', 'pkgsrc-source', 'work-parent'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(all(p.is_absolute() for p in vars(args).values()), 'Use absolute paths')
    repo = Path(__file__).resolve().parents[4]
    print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
    work = Path(tempfile.mkdtemp(prefix='pkgsrc-native-test-env-', dir=args.work_parent))
    try:
        config = work / 'mk.conf'
        config.write_text('# Isolated source-metadata check.\n')

        def query(relative, cross, *, broken=False):
            body = (repo / relative / 'Makefile').read_text()
            body = '\n'.join(line for line in body.splitlines() if not line.startswith('.include '))
            if broken:
                require(body.count('TEST_ENV+= LD_LIBRARY_PATH=') == 1, 'Causal input changed')
                body = body.replace('TEST_ENV+= LD_LIBRARY_PATH=', 'TEST_ENV+= ${SHLIB_PATH_VAR}=')
            fixture = work / 'fixture.mk'
            fixture.write_text('NATIVE_OPSYS=NetBSD\nNATIVE_OS_VERSION=11.0\n'
                'NATIVE_OPSYS_VERSION=110000\nHOST_MACHINE_ARCH=x86_64\nMACHINE_ARCH=x86_64\n'
                'OBJECT_FMT=ELF\nUSE_CROSS_COMPILE=no\nMAKECONF=' + str(config) + '\n' +
                '.include "' + str(args.pkgsrc_source / 'mk/bsd.prefs.mk') + '"\n'
                'DISCOVERED_OPSYS:=${OPSYS}\nDISCOVERED_SHLIB:=${SHLIB_TYPE}\n'
                'USE_CROSS_COMPILE=' + ('yes' if cross else 'no') + '\n' +
                'WRKDIR=/native/work\nWRKSRC=/native/source\nCMAKE_BUILD_DIR=cmake-pkgsrc-build\n' + body +
                '\nshow:\n\t@printf \'%s\\n\' ${DISCOVERED_OPSYS:Q} ${DISCOVERED_SHLIB:Q} '
                '${SHLIB_PATH_VAR:Uundefined:Q} \'TEST_ENV=\'${TEST_ENV:Q}\n')
            result = subprocess.run([str(args.bmake), '-r', '-f', str(fixture), 'show', 'WRKSRC=/native/source'],
                cwd=args.pkgsrc_source / relative.removeprefix('pkgsrc/'), capture_output=True, text=True)
            require(result.returncode == 0, result.stdout + result.stderr)
            lines = result.stdout.splitlines()
            require(lines[:3] == ['NetBSD', 'ELF', 'undefined'], 'Unexpected pkgsrc platform: ' + result.stdout)
            require(len(lines) == 4, 'Unexpected metadata output: ' + result.stdout)
            leaf = 'effcee' if relative.endswith('/effcee') else 'source'
            path = '/native/source/cmake-pkgsrc-build/' + leaf
            expected = [] if cross else ['LD_LIBRARY_PATH=' + path, 'DYLD_LIBRARY_PATH=' + path]
            require(lines[3].startswith('TEST_ENV='), 'Missing environment field')
            return lines[3].removeprefix('TEST_ENV=').split() == expected

        for relative in ('pkgsrc/devel/effcee', 'pkgsrc/parallel/spirv-tools'):
            for cross in (False, True):
                require(query(relative, cross), relative + ': incorrect test environment')
                print('PASS: ' + relative + (' cross guard' if cross else ' native platform environment'))
            require(not query(relative, False, broken=True), relative + ': causal fault was accepted')
            print('PASS: ' + relative + ' undefined-variable causal rejection')
        print('PASS: six platform/guard/causal checks; no build or target execution')
    finally:
        print(subprocess.check_output(['df', '-k', str(work)], text=True), end='')
        shutil.rmtree(work)
        require(not work.exists(), 'Own fixture remains')
        print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
        print('Removed owned fixture: ' + str(work))


if __name__ == '__main__':
    main()
