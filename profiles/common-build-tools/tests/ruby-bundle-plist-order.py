#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check longest-first Ruby PLIST substitutions without pkgsrc or system tools."""

import argparse
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXPRESSION = '${RUBY_BUNDLE_MODULES:@m@${m:C/./x/g}-${m}@:Or:C/^x*-//}'


def run(argv, *, input_text=None):
    return subprocess.run(argv, input=input_text, capture_output=True, text=True, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--awk', type=Path, required=True)
    args = parser.parse_args()

    profile_patch = (ROOT / 'patches/pkgsrc-ruby-platform-tools.patch').read_text()
    if EXPRESSION not in profile_patch:
        raise ValueError('profile patch no longer contains the tested bmake expression')

    with tempfile.TemporaryDirectory(prefix='ruby-bundle-plist-order-') as tmp:
        makefile = Path(tmp) / 'Makefile'
        makefile.write_text(
            'RUBY_BUNDLE_MODULES= foo barfoo\n'
            f'_RUBY_BUNDLE_MODULES= {EXPRESSION}\n'
        )
        modules = run([str(args.bmake), '-r', '-f', str(makefile),
                       '-V', '${_RUBY_BUNDLE_MODULES}']).stdout.split()
        if modules != ['barfoo', 'foo']:
            raise ValueError(f'expected longest-first module order, got {modules!r}')

        # Mirror platform.mk's unanchored sub(/module-version/, ...), with the
        # shorter module name colliding at the end of the longer one.
        awk_program = ' '.join(
            f'{{ sub(/{module}-1\\.0/, "{module}-${{RUBY_{module.upper()}_VER}}"); }}'
            for module in modules
        ) + ' { print; }'
        output = run([str(args.awk), awk_program],
                     input_text='barfoo-1.0 foo-1.0\n').stdout
        expected = 'barfoo-${RUBY_BARFOO_VER} foo-${RUBY_FOO_VER}\n'
        if output != expected:
            raise ValueError(f'PLIST rewrite mismatch: {output!r} != {expected!r}')

    print('PASS: bmake orders suffix-colliding gem names longest first; AWK rewrites both PLIST entries correctly')


if __name__ == '__main__':
    main()
