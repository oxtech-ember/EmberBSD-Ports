#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Keep the generated GCC new-file hunk equal to the shared diagnostic source."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'profiles/common-build-tools/files/emberbsd-configure-diagnostics.sh'
PATCH = ROOT/'profiles/development-toolchain/patches/gcc-sdk-configure-diagnostics.patch'


def generated(text, source):
    start = text.index('--- config/emberbsd-sdk-diagnostics.sh.orig\n')
    end = text.index('--- c++tools/configure.orig\n', start)
    lines = source.splitlines(keepends=True)
    assert source.endswith('\n') and lines
    hunk = ('--- config/emberbsd-sdk-diagnostics.sh.orig\n'
            '+++ config/emberbsd-sdk-diagnostics.sh\n'
            '@@ -0,0 +1,' + str(len(lines)) + ' @@\n' +
            ''.join('+' + line for line in lines))
    return text[:start] + hunk + text[end:]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    original = PATCH.read_text()
    expected = generated(original, SOURCE.read_text())
    if args.write:
        PATCH.write_text(expected)
    elif original != expected:
        parser.exit(1, 'generated GCC diagnostic helper differs from its canonical source\n')
