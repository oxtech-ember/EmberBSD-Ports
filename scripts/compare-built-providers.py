#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Compare the consumer-visible payload of two locally built pkgsrc archives."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cross_bulk_provider import package_interface


def inspect(path):
    metadata = {}
    files = {}
    digests = {}
    elf_files = set()
    with tarfile.open(path, 'r|*') as archive:
        for item in archive:
            name = PurePosixPath(item.name)
            if name.is_absolute() or '..' in name.parts or not name.parts:
                raise ValueError('invalid package member path')
            key = name.as_posix()
            if name.name.startswith('+') and len(name.parts) == 1:
                if key in metadata or not item.isfile() or item.size > 16 * 1024 * 1024:
                    raise ValueError('invalid package metadata: ' + key)
                metadata[key] = archive.extractfile(item).read()
                continue
            if key in files:
                raise ValueError('duplicate package member: ' + key)
            attributes = (item.mode, item.uid, item.gid, item.uname, item.gname)
            if item.isfile():
                sha = hashlib.sha256()
                registered = hashlib.md5(usedforsecurity=False)
                stream = archive.extractfile(item)
                first = stream.read(4)
                if first == b'\x7fELF':
                    elf_files.add(name)
                sha.update(first)
                registered.update(first)
                for block in iter(lambda: stream.read(1 << 20), b''):
                    sha.update(block)
                    registered.update(block)
                digests[name] = (registered.hexdigest(), sha.hexdigest())
                payload = ('file', sha.hexdigest())
            elif item.issym():
                payload = ('symlink', item.linkname)
            elif item.isdir():
                payload = ('directory',)
            else:
                raise ValueError('unsupported package member: ' + key)
            files[key] = (attributes, payload, {k: v for k, v in item.pax_headers.items()
                                                if k not in ('mtime', 'atime', 'ctime', 'path', 'linkpath')})

    def registered_file(relative, expected):
        if relative not in digests or digests[relative][0] != expected:
            raise ValueError('archive file differs from registered contents: ' + str(relative))
        return digests[relative][1]

    def registered_elf(relative, expected):
        if relative not in elf_files:
            raise ValueError('declared provider is not an ELF file: ' + str(relative))
        return registered_file(relative, expected)

    def registered_link(relative, expected):
        entry = files.get(str(relative))
        if entry is None or entry[1] != ('symlink', expected):
            raise ValueError('archive link differs from registered contents: ' + str(relative))

    contents = metadata.get('+CONTENTS', b'')
    names = [line[6:] for line in contents.decode().splitlines() if line.startswith('@name ')]
    if len(names) != 1 or not names[0]:
        raise ValueError('missing or ambiguous package identity')
    if '+BUILD_INFO' not in metadata:
        raise ValueError('missing package build info')
    identity = package_interface(names[0], contents, metadata['+BUILD_INFO'].decode(),
                                 registered_elf, inspect_file=registered_file, inspect_link=registered_link)
    # Installation hooks and extra package administration records can affect
    # the installed payload even when every archived program is unchanged.
    informational = {'+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION', '+COMMENT', '+DESC',
                     '+SIZE_PKG', '+SIZE_ALL'}
    controls = {key: hashlib.sha256(value).hexdigest() for key, value in metadata.items()
                if key not in informational}
    return names[0], identity, files, controls


def compare(before, after):
    old, old_interface, old_files, old_controls = inspect(before)
    new, new_interface, new_files, new_controls = inspect(after)
    changed = sorted(name for name in old_files.keys() | new_files.keys()
                     if old_files.get(name) != new_files.get(name))
    same = old_interface == new_interface and not changed and old_controls == new_controls
    return dict(before=old, after=new, same_provider_inputs=same, changed_files=changed,
                package_interface_changed=old_interface != new_interface,
                installation_controls_changed=old_controls != new_controls)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.before, args.after), indent=2))
    except (OSError, UnicodeError, ValueError, EOFError, tarfile.TarError) as exc:
        parser.exit(1, 'cannot establish package equivalence: ' + str(exc) + '\n')
