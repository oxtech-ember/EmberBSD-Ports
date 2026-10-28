#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), inspector protocol Gitiles source normalization.
"""Verify the inspector protocol Git tree and normalize Gitiles' request-time tar metadata."""
import argparse
import os
from pathlib import Path
import re
import tempfile
import sys
import urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'lang/llvm/files'))
import sdk_source


def load_sdk(arguments):
    _, arguments = sdk_source.load_sdk(arguments)
    from emberbsd_sdk import gitiles
    if getattr(gitiles, 'GITILES_API', None) != 1:
        raise ValueError('selected SDK lacks Gitiles API 1')
    globals()['gitiles'] = gitiles
    return arguments


def require(condition, message):
    if not condition:
        raise ValueError(message)


def publish(raw, expected_tree, output, root_name):
    require(output.is_absolute() and not os.path.lexists(output), 'use a new absolute output file')
    normalized = gitiles.normalize(raw, expected_tree, root_name=root_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=output.name + '.', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(normalized)
            os.fchmod(stream.fileno(), 0o644)
        # An existing cache entry belongs to its writer. Never overwrite it.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink()
    return len(normalized)


def main():
    arguments = load_sdk(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--tree', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root-name', required=True)
    parser.add_argument('--input-archive', type=Path,
                        help='use a previously obtained Gitiles archive for offline verification')
    args = parser.parse_args(arguments)
    require(re.fullmatch('[0-9a-f]{40}', args.revision) is not None, 'use a full pinned inspector protocol revision')
    require(re.fullmatch('[0-9a-f]{40}', args.tree) is not None, 'use a full pinned inspector protocol tree')
    if args.input_archive:
        require(args.input_archive.stat().st_size <= gitiles.MAX_ARCHIVE, 'inspector protocol archive is too large')
        raw = args.input_archive.read_bytes()
    else:
        url = 'https://chromium.googlesource.com/deps/inspector_protocol/+archive/' + args.revision + '.tar.gz'
        with urllib.request.urlopen(url, timeout=120) as response:
            raw = response.read(gitiles.MAX_ARCHIVE + 1)
    size = publish(raw, args.tree, args.output, args.root_name)
    print(f'Verified inspector protocol {args.revision} tree {args.tree}; wrote {size} normalized bytes.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        raise SystemExit(f'inspector protocol source: {exc}')
