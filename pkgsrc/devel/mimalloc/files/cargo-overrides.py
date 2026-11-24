#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select the common mimalloc library for a Cargo links build-script override."""
import argparse
import json
from pathlib import Path


def write_override(libdir, output, library="mimalloc"):
    if not libdir.is_absolute() or not libdir.is_dir():
        raise ValueError('mimalloc library search must be the prepared buildlink directory')
    if library not in ('mimalloc', 'mimalloc-embed'):
        raise ValueError('unknown shared mimalloc library')
    if not any((libdir / ('lib' + library + suffix)).is_file() for suffix in ('.so', '.dylib')):
        raise ValueError('selected shared library is missing from buildlink: ' + library)
    output.write_text('[mimalloc_sys2]\nrustc-link-lib = ' + json.dumps(['dylib=' + library]) +
                      '\nrustc-link-search = ' + json.dumps([str(libdir)], ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--libdir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--library', choices=('mimalloc', 'mimalloc-embed'), default='mimalloc')
    try:
        args = parser.parse_args()
        write_override(args.libdir, args.output, args.library)
    except (OSError, ValueError) as error:
        parser.exit(1, f'mimalloc Cargo override: {error}\n')


if __name__ == '__main__':
    main()
