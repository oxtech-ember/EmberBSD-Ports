#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native Mach-O package metadata regression.
"""Check native defaults and optional metadata from an existing package stage."""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def run(argv):
    result = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--pkgsrc', type=Path)
    parser.add_argument('--makeconf', type=Path)
    parser.add_argument('--package', default='textproc/expat')
    parser.add_argument('--expected-library', type=Path)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    # defaults.mk.conf includes the exported EMBERBSD-VERSIONS.MK beside it.
    defaults = args.work / 'EMBERBSD-DEFAULTS-MK.CONF'
    shutil.copy2(ROOT / 'pkgsrc/defaults.mk.conf', defaults)
    shutil.copy2(ROOT / 'pkgsrc/versions.mk', args.work / 'EMBERBSD-VERSIONS.MK')
    makefile = args.work / 'Makefile'
    makefile.write_text('BSD_PKG_MK= yes\n.include "' + str(defaults) + '"\n')
    for system, cross, expected in [('Darwin', 'no', 'yes'), ('Darwin', 'yes', ''),
                                     ('Linux', 'no', ''), ('NetBSD', 'no', '')]:
        value = run([args.bmake, '-r', '-f', str(makefile), 'OPSYS=' + system,
                     'USE_CROSS_COMPILE=' + cross, '-V', '${MACHO_USE_LOAD_COMMANDS}']).strip()
        assert value == expected, (system, cross, value, expected)
    print('PASS: native Darwin resolves load commands; other contexts retain their defaults')
    if args.pkgsrc:
        assert args.makeconf and args.expected_library
        config = args.work / 'mk.conf'
        config.write_text('.include "' + str(args.makeconf.resolve()) + '"\n.include "' + str(defaults) + '"\n')
        output = args.work / '+BUILD_INFO'
        log = run([args.bmake, '-C', str(args.pkgsrc / args.package),
                   'MAKECONF=' + str(config), '_BUILD_INFO_FILE=' + str(output), str(output)])
        (args.work / 'metadata.log').write_text(log)
        requires = [line.split('=', 1)[1] for line in output.read_text().splitlines()
                    if line.startswith('REQUIRES=')]
        assert str(args.expected_library.resolve(strict=True)) in requires, requires
        assert not any(item.startswith('@') for item in requires), requires
        print('PASS: actual staged package retains the absolute selected runtime requirement')
    print('SCOPE: metadata only; no package installation or runtime qualification')


if __name__ == '__main__':
    main()
