# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Restricted base/comp tar.xz extraction. No links exist during file writes."""
import lzma
import os
from pathlib import Path
import tarfile


def extract(archives, root):
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.paths import canonical_existing, inside
    if os.path.lexists(root):
        raise SDKError('Use a fresh extraction directory')
    os.mkdir(root)
    root = canonical_existing(root)
    links, inventory = {}, {}

    def member_path(name):
        name = name.removeprefix('./').removesuffix('/')
        if name in ('', '.'):
            return root
        if name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')) or any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise SDKError('Unsafe archive member')
        result = root + '/' + name
        if not inside(result, root):
            raise SDKError('Archive path escapes sysroot')
        return result

    def exact(stream, size):
        data = stream.read(size)
        if len(data) != size:
            raise SDKError('Truncated archive member')
        return data

    for archive in archives:
        members = set()
        try:
            with lzma.open(archive, 'rb') as stream:
                while True:
                    header = exact(stream, 512)
                    if header == bytes(512):
                        if exact(stream, 512) != bytes(512):
                            raise SDKError('Nonzero data after tar end marker')
                        padding = 0
                        while block := stream.read(65536):
                            padding += len(block)
                            if padding > 1024 * 1024:
                                raise SDKError('Excessive trailing tar padding')
                            if any(block):
                                raise SDKError('Nonzero data after tar end marker')
                        break
                    item = tarfile.TarInfo.frombuf(header, 'utf-8', 'strict')
                    path = member_path(item.name)
                    if path == root:
                        if item.type != tarfile.DIRTYPE or item.size:
                            raise SDKError('Archive root must be a directory')
                        continue
                    relative, kind, mode = os.path.relpath(path, root), item.type, item.mode & 0o7777
                    previous = inventory.get(relative)
                    if previous:
                        if kind == tarfile.DIRTYPE:
                            if previous['type'] != 'directory':
                                raise SDKError('Conflicting archive directory: ' + relative)
                        else:
                            identical_alias = (relative not in members and kind == tarfile.SYMTYPE and previous['type'] == 'symlink'
                                               and previous['mode'] == mode and previous['archive_link'] == item.linkname and item.size == 0)
                            if not identical_alias:
                                raise SDKError('Duplicate non-directory archive member: ' + relative)
                            members.add(relative)
                            continue
                    members.add(relative)
                    if kind not in (tarfile.REGTYPE, tarfile.AREGTYPE) and item.size:
                        raise SDKError('Non-file archive entry has data: ' + relative)
                    if kind == tarfile.DIRTYPE:
                        os.makedirs(path, exist_ok=True)
                        os.chmod(path, mode)
                        inventory[relative] = dict(type='directory', mode=mode)
                    elif kind in (tarfile.REGTYPE, tarfile.AREGTYPE):
                        if item.size < 0 or item.size > 1024**3:
                            raise SDKError('Archive member exceeds 1 GiB')
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        remaining = item.size
                        with open(path, 'xb') as output:
                            while remaining:
                                block = exact(stream, min(remaining, 1024 * 1024))
                                output.write(block)
                                remaining -= len(block)
                        exact(stream, (-item.size) % 512)
                        os.chmod(path, mode)
                        inventory[relative] = dict(type='file', mode=mode, sha256=sha256_file(path))
                    elif kind in (tarfile.LNKTYPE, tarfile.SYMTYPE):
                        if kind == tarfile.LNKTYPE:
                            target = member_path(item.linkname)
                        elif item.linkname.startswith('/'):
                            target = os.path.normpath(root + item.linkname)
                        else:
                            target = os.path.normpath(os.path.join(os.path.dirname(path), item.linkname))
                        if target != root and not inside(target, root):
                            raise SDKError('Archive link escapes sysroot')
                        links[path] = (kind, target)
                        inventory[relative] = dict(type='hardlink' if kind == tarfile.LNKTYPE else 'symlink', mode=mode, archive_link=item.linkname)
                    else:
                        raise SDKError('Unsupported archive entry: ' + relative)
        except (lzma.LZMAError, EOFError) as error:
            raise SDKError('xz failed: ' + str(error)) from error
    hardlinks = {p: target for p, (kind, target) in links.items() if kind == tarfile.LNKTYPE}
    while hardlinks:
        complete = []
        for path, target in hardlinks.items():
            if not os.path.isfile(target) or os.path.islink(target):
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            os.link(target, path)
            complete.append(path)
        if not complete:
            raise SDKError('Unresolved or cyclic archive hardlinks')
        for path in complete:
            del hardlinks[path]
    for path, (kind, target) in links.items():
        if kind != tarfile.SYMTYPE:
            continue
        parent = os.path.dirname(path)
        while parent != root:
            if os.path.islink(parent):
                raise SDKError('Archive link has a symlink parent')
            parent = os.path.dirname(parent)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        normalized = os.path.relpath(target, os.path.dirname(path))
        os.symlink(normalized, path)
        inventory[os.path.relpath(path, root)]['link'] = normalized
    return inventory
