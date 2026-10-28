#!/usr/bin/env python3
"""Check that an SDL2 consumer evaluates when USE_CROSS_COMPILE is unset."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import subprocess
import sys

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True, help='bmake with the host mk files')
    parser.add_argument('--makeconf', required=True, help='MAKECONF for the target')
    parser.add_argument('--consumer', required=True, help='exported graphics/SDL2_image')
    args = parser.parse_args()
    # SDL2_image reads this buildlink3.mk when USE_CROSS_COMPILE is not defined.
    result = subprocess.run([args.bmake, 'MAKECONF=' + args.makeconf, '-v', 'PKGNAME'],
                            cwd=args.consumer, capture_output=True, text=True)
    if result.returncode != 0 or 'is undefined' in result.stderr:
        print(result.stderr, file=sys.stderr)
        print('FAIL: SDL2 buildlink3.mk reads an undefined USE_CROSS_COMPILE.')
        return 1
    print('PASS: ' + result.stdout.strip())
    return 0


if __name__ == '__main__':
    sys.exit(main())
