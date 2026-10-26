#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), GN Gitiles source normalization.
"""Verify the GN Git tree and normalize Gitiles' request-time tar metadata."""
import argparse
import gzip
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
import urllib.request

MAX_ARCHIVE = 16 * 1024 * 1024
MAX_CONTENT = 32 * 1024 * 1024
MAX_MEMBERS = 4096
MAX_TAR = MAX_CONTENT + MAX_MEMBERS * 4096


class SourceError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise SourceError(message)


def git_hash(kind, data):
    return hashlib.sha1(kind.encode() + b' ' + str(len(data)).encode() + b'\0' + data).digest()


def tree_hash(files):
    root = {}
    for name, (mode, data) in files.items():
        parts = name.split('/')
        node = root
        for part in parts[:-1]:
            require(part not in node or isinstance(node[part], dict), 'file/directory collision')
            node = node.setdefault(part, {})
        require(parts[-1] not in node, 'duplicate Git path')
        node[parts[-1]] = (mode, git_hash('blob', data))

    def digest(node):
        entries = []
        for name, value in node.items():
            directory = isinstance(value, dict)
            mode, blob = ('40000', digest(value)) if directory else value
            encoded = name.encode('utf-8')
            entries.append((encoded + (b'/' if directory else b''),
                            mode.encode() + b' ' + encoded + b'\0' + blob))
        return git_hash('tree', b''.join(row for _, row in sorted(entries)))

    return digest(root).hex()


def read_gitiles(raw, expected_tree):
    require(len(raw) <= MAX_ARCHIVE, 'GN source archive is too large')
    with gzip.GzipFile(fileobj=io.BytesIO(raw), mode='rb') as compressed:
        unpacked = compressed.read(MAX_TAR + 1)
    require(len(unpacked) <= MAX_TAR, 'expanded GN archive is too large')
    files, seen, folded, directories = {}, set(), {}, set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode='r:') as archive:
        for member in archive:
            require(len(seen) < MAX_MEMBERS, 'too many GN source entries')
            name = member.name.rstrip('/') if member.isdir() else member.name
            path = PurePosixPath(name)
            require(name and str(path) == name and not path.is_absolute() and
                    all(part not in ('', '.', '..') for part in path.parts) and
                    '\\' not in name and '\0' not in name, 'unsafe GN source path')
            require(name not in seen, 'duplicate GN source path')
            seen.add(name)
            for index in range(1, len(path.parts) + 1):
                parent = '/'.join(path.parts[:index])
                key = parent.casefold()
                require(key not in folded or folded[key] == parent,
                        'case-colliding GN source path')
                folded[key] = parent
            # GN's pinned tree has only regular files. Do not allow archive
            # symlinks, hardlinks, devices or metadata to create host inputs.
            require(member.isdir() or member.isfile(), 'unsupported GN source entry type')
            if member.isdir():
                directories.add(name)
                continue
            require(0 <= member.size <= MAX_CONTENT - total, 'GN source content is too large')
            require(member.mode & 0o7777 in (0o644, 0o755), 'unsupported GN source file mode')
            total += member.size
            stream = archive.extractfile(member)
            require(stream is not None, 'missing GN source content')
            with stream:
                data = stream.read(member.size + 1)
            require(len(data) == member.size, 'truncated GN source content')
            mode = '100755' if member.mode & 0o111 else '100644'
            files[name] = mode, data
    parents = {'/'.join(name.split('/')[:index]) for name in files
               for index in range(1, len(name.split('/')))}
    require(directories <= parents, 'directory without Git-tracked children')
    require(files and tree_hash(files) == expected_tree, 'GN archive does not match the pinned Git tree')
    return files


def normalized_tar(files):
    output = io.BytesIO()
    # USTAR has no generated PAX timestamps or gzip implementation dependency.
    # Only Git-tracked files are materialized; their parent directories follow
    # from their paths. All source bytes and executable bits remain unchanged.
    with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, (mode, data) in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = int(mode, 8) & 0o777
            member.mtime = member.uid = member.gid = 0
            member.uname = member.gname = ''
            archive.addfile(member, io.BytesIO(data))
    return output.getvalue()


def publish(raw, expected_tree, output):
    require(output.is_absolute() and not os.path.lexists(output), 'use a new absolute output file')
    normalized = normalized_tar(read_gitiles(raw, expected_tree))
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--tree', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--input-archive', type=Path,
                        help='use a previously obtained Gitiles archive for offline verification')
    args = parser.parse_args()
    require(re.fullmatch('[0-9a-f]{40}', args.revision) is not None, 'use a full pinned GN revision')
    require(re.fullmatch('[0-9a-f]{40}', args.tree) is not None, 'use a full pinned GN tree')
    if args.input_archive:
        require(args.input_archive.stat().st_size <= MAX_ARCHIVE, 'GN source archive is too large')
        raw = args.input_archive.read_bytes()
    else:
        url = 'https://gn.googlesource.com/gn/+archive/' + args.revision + '.tar.gz'
        with urllib.request.urlopen(url, timeout=120) as response:
            raw = response.read(MAX_ARCHIVE + 1)
    size = publish(raw, args.tree, args.output)
    print(f'Verified GN {args.revision} tree {args.tree}; wrote {size} normalized bytes.')


if __name__ == '__main__':
    try:
        main()
    except (SourceError, OSError, ValueError, tarfile.TarError) as exc:
        raise SystemExit(f'GN source: {exc}')
