#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Build and execute littlefs open-unlinked allocation regressions."""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
TEST = HERE / 'tests/open-unlinked.c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', required=True, help='selected host C compiler')
    parser.add_argument('--source', required=True, type=Path,
                        help='prepared littlefs source directory')
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='littlefs-open-unlinked-') as tmp:
        binary = Path(tmp) / 'open-unlinked'
        subprocess.run([args.cc, '-Wall', '-Wextra', '-Werror', '-I', str(source),
                        str(TEST), str(source / 'lfs.c'), str(source / 'lfs_util.c'),
                        '-o', str(binary)], check=True)
        for case in ('unlink', 'overwrite', 'inline-sync'):
            result = subprocess.run([str(binary), case], text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise SystemExit(f'{case} regression failed (exit {result.returncode}):\n'
                                 f'{result.stdout}{result.stderr}')
            print(f'{case}: {result.stdout.strip()}')


if __name__ == '__main__':
    main()
