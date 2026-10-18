#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted installed GUI/CAD API consumer preparation.
"""Build consumers with GCC16. Do not install packages or start a target."""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True, type=Path)
    parser.add_argument('--sysroot', required=True, type=Path)
    parser.add_argument('--cross-tools', required=True, type=Path)
    parser.add_argument('--cmake', required=True, type=Path)
    parser.add_argument('--packages', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error('use the selected CPython 3.15 host profile')
    sdk_source = args.sdk_source.resolve(strict=True)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(sdk_source / 'src'))
    import emberbsd_sdk
    if emberbsd_sdk.API_VERSION != 1:
        parser.error('require EmberBSD SDK host API 1')
    if Path(emberbsd_sdk.__file__).resolve().parent != sdk_source / 'src/emberbsd_sdk':
        parser.error('the SDK import did not use the selected source')
    from build import prepare
    archive, identity = prepare(args)
    print(archive)
    print(identity)


if __name__ == '__main__':
    main()
