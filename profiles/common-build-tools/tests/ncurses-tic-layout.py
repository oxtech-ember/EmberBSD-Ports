#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check actual native tic database layout.
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tic', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--readelf', type=Path)
    parser.add_argument('--valgrind', type=Path)
    args = parser.parse_args()
    if not args.work.is_absolute() or args.work.exists():
        parser.error('--work must be a new absolute directory')
    args.work.mkdir()
    source = args.work / 'layout.src'
    source.write_text('emberbsd-tic-layout|EmberBSD-tic-layout|Private tic layout fixture,\n cols#80, lines#24,\n')
    output = args.work / 'database'
    command = [str(args.tic), '-x', '-o', str(output), str(source)]
    if args.valgrind:
        command = [str(args.valgrind), '--leak-check=full', '--errors-for-leak-kinds=definite,indirect,possible', '--error-exitcode=99'] + command
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (args.work / 'tic.log').write_text(result.stdout + result.stderr)
    result.check_returncode()
    lower = output / '65/emberbsd-tic-layout'
    upper = output / '45/EmberBSD-tic-layout'
    assert lower.is_file() and upper.is_file(), 'tic did not use the target hexadecimal layout'
    assert lower.read_bytes() == upper.read_bytes()
    assert not (output / 'e/emberbsd-tic-layout').exists()
    if args.readelf:
        result = subprocess.run([str(args.readelf), '-dW', str(args.tic)], capture_output=True, text=True, check=True)
        (args.work / 'dynamic.log').write_text(result.stdout + result.stderr)
        assert not any('NEEDED' in line and 'libncurses' in line for line in result.stdout.splitlines())
    print('PASS: actual private tic hexadecimal layout and matching aliases')


if __name__ == '__main__':
    main()
