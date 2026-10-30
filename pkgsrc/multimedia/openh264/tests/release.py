#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted openh264 release regression.
"""Check the selected openh264 release, its SONAME, and the ABI floor.

openh264 2.6.0 lacks the 2.7.0 decoder bounds checks (for example
cisco/openh264#3965 and #3967). The recipe must select 2.7.0 or newer, the
PLIST must match the SONAME of the extracted source, and consumers must not
accept an older package.
"""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

MINIMUM = (2, 7, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'bmake'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    recipe = args.pkgsrc / 'multimedia/openh264'
    with tempfile.TemporaryDirectory(prefix='openh264-release-') as temporary:
        base = [str(args.bmake), 'MAKECONF=' + str(args.makeconf),
                'WRKOBJDIR=' + str(Path(temporary).resolve() / 'objects')]

        def run(*argv):
            proc = subprocess.run([*base, *argv], cwd=recipe, capture_output=True, text=True)
            assert proc.returncode == 0, (argv, proc.stdout[-2000:], proc.stderr[-2000:])
            return proc.stdout.strip()

        version = run('-V', '${PKGVERSION_NOREV}')
        assert tuple(int(x) for x in version.split('.')) >= MINIMUM, version
        run('patch')
        source = Path(run('-V', '${WRKSRC}'))
        makefile = (source / 'Makefile').read_text()
        assert re.search(r'^FULL_VERSION := %s$' % re.escape(version), makefile, re.M), version
        major = re.search(r'^SHAREDLIB_MAJORVERSION=(\d+)$', makefile, re.M).group(1)
        plist = (recipe / 'PLIST').read_text().split()
        assert 'lib/libopenh264.so.' + major in plist, (major, plist)
        assert 'lib/libopenh264.so.${PKGVERSION}' in plist, plist
        abi = run('-V', '${BUILDLINK_ABI_DEPENDS.openh264}')
    floor = re.search(r'openh264>=([0-9.]+)', (recipe / 'buildlink3.mk').read_text()
                      .split('BUILDLINK_ABI_DEPENDS.openh264', 1)[1]).group(1)
    assert floor == version, (floor, version, abi)
    print('PASS: openh264 %s, SONAME %s, ABI floor %s' % (version, major, floor))


if __name__ == '__main__':
    main()
