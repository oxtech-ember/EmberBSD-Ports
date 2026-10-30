#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select the common mimalloc library for a Cargo links build-script override."""
import argparse
import json
from pathlib import Path


def write_override(libdir, output):
    if not libdir.is_absolute() or not libdir.is_dir():
        raise ValueError('mimalloc library search must be the prepared buildlink directory')
    if not any((libdir / name).is_file() for name in ('libmimalloc.so', 'libmimalloc.dylib')):
        raise ValueError('selected shared mimalloc library is missing from buildlink')
    output.write_text('[mimalloc_sys2]\nrustc-link-lib = ["dylib=mimalloc"]\nrustc-link-search = ' +
                      json.dumps([str(libdir)], ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--libdir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    try:
        args = parser.parse_args()
        write_override(args.libdir, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f'mimalloc Cargo override: {error}\n')


if __name__ == '__main__':
    main()
