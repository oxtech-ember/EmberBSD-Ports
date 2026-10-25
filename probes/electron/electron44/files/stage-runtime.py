#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD. Electron build/zip.py owns the runtime member selection.
"""Stage Electron 44's own dist.zip. This does not accept a build or package."""

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import struct
import sys
import tempfile
import unicodedata
import zipfile

VERSION = b'44.9.3'
MAX_ENTRIES = 65536
MAX_MEMBER = 2 * 1024 ** 3
MAX_TOTAL = 8 * 1024 ** 3
MAX_CENTRAL_DIRECTORY = 16 * 1024 ** 2


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_sdk(source):
    root = Path(source).resolve(strict=True)
    require(Path(source).is_absolute(), 'use an absolute SDK source')
    package = root / 'src/emberbsd_sdk'
    sys.path.insert(0, str(root / 'src'))
    modules = [importlib.import_module('emberbsd_sdk' + suffix) for suffix in
               ('', '.paths', '.publication', '.elf', '.targets')]
    for module in modules:
        name = '__init__' if module.__name__ == 'emberbsd_sdk' else module.__name__.split('.')[-1]
        require(Path(module.__file__).resolve(strict=True) == package / (name + '.py'),
                'SDK module origin differs: ' + module.__name__)
    require(modules[0].API_VERSION == 1, 'SDK API 1 is required')
    require(modules[2].DIRECTORY_PUBLICATION_API == 1, 'SDK publication API 1 is required')
    return modules[1:]


def member_name(info):
    value = info.orig_filename
    require(value == info.filename and not any(ord(c) < 32 or ord(c) == 127 for c in value),
            'ZIP member has a control character')
    require('\\' not in value and ':' not in value, 'ZIP member has a non-POSIX path')
    while value.startswith('./'):
        value = value[2:]
    value = value[:-1] if value.endswith('/') else value
    parts = PurePosixPath(value).parts
    require(parts and not value.startswith('/') and
            all(part not in ('', '.', '..') for part in value.split('/')),
            'ZIP member escapes or aliases the payload')
    return '/'.join(parts)


def zip_members(archive):
    infos = archive.infolist()
    require(0 < len(infos) <= MAX_ENTRIES, 'ZIP member count exceeds the limit')
    rows, names, spelling, total = [], set(), {}, 0
    for info in infos:
        name = member_name(info)
        key = unicodedata.normalize('NFC', name).casefold()
        require(key not in names, 'ZIP contains colliding member names')
        names.add(key)
        parts = name.split('/')
        for length in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:length])
            folded = unicodedata.normalize('NFC', prefix).casefold()
            require(spelling.setdefault(folded, prefix) == prefix,
                    'ZIP contains colliding parent names')
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        kind = kind or (stat.S_IFDIR if info.is_dir() else stat.S_IFREG)
        require(kind in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK), 'ZIP contains a special file')
        require(not (mode & 0o7000), 'ZIP contains unsupported privilege mode bits')
        require(not info.flag_bits & 1 and info.compress_type in
                (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'ZIP uses unsupported encryption or compression')
        require(0 <= info.file_size <= MAX_MEMBER, 'ZIP member exceeds the size limit')
        require(kind != stat.S_IFDIR or info.file_size == 0, 'ZIP directory contains data')
        require(kind != stat.S_IFLNK or info.file_size <= 4096, 'ZIP link target exceeds the limit')
        total += info.file_size
        require(total <= MAX_TOTAL, 'ZIP payload exceeds the size limit')
        permissions = stat.S_IMODE(mode) if mode else (0o755 if kind == stat.S_IFDIR else 0o644)
        rows.append((name, kind, permissions, info))
    kinds = {name: kind for name, kind, _, _ in rows}
    for name in kinds:
        parent = posixpath.dirname(name)
        while parent:
            require(kinds.get(parent, stat.S_IFDIR) == stat.S_IFDIR,
                    'ZIP member has a non-directory parent')
            parent = posixpath.dirname(parent)
    return rows


def check_zip_directory(handle, size):
    # Bound ZipFile's central-directory allocation before it reads that table.
    # This first implementation supports a single standard central directory.
    require(22 <= size <= MAX_TOTAL, 'ZIP file exceeds the size limit')
    handle.seek(max(0, size - 65557))
    tail = handle.read(65557)
    offset = tail.rfind(b'PK\x05\x06')
    require(offset >= 0 and len(tail) - offset >= 22, 'ZIP end record is missing')
    record = struct.unpack_from('<4s4H2IH', tail, offset)
    _, disk, central_disk, on_disk, entries, length, start, comment = record
    require(offset + 22 + comment == len(tail), 'ZIP end record is malformed')
    require(disk == central_disk == 0 and on_disk == entries and entries < 65535,
            'multi-disk and ZIP64 archives are unsupported')
    require(length != 0xffffffff and start != 0xffffffff and
            tail[max(0, offset - 20):offset - 16] != b'PK\x06\x07',
            'ZIP64 archives are unsupported')
    absolute = size - len(tail) + offset
    require(0 < length <= MAX_CENTRAL_DIRECTORY and start + length == absolute,
            'ZIP central directory exceeds or differs from its bounds')
    handle.seek(0)
    require(handle.read(4) == b'PK\x03\x04', 'ZIP has a non-ZIP prefix')
    handle.seek(0)


def read_member(archive, info, output):
    size = 0
    digest = hashlib.sha256()
    with archive.open(info) as source:
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            require(size <= info.file_size, 'ZIP expanded beyond its declared size')
            output.write(chunk)
            digest.update(chunk)
    require(size == info.file_size, 'ZIP member size differs')
    return digest.hexdigest()


def extract(archive, stage, rows):
    links, facts = {}, []
    for name, kind, mode, info in rows:
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if kind == stat.S_IFDIR:
            target.mkdir(exist_ok=True)
            facts.append(dict(path=name, directory=True, mode=mode))
        elif kind == stat.S_IFREG:
            with target.open('xb') as output:
                digest = read_member(archive, info, output)
            target.chmod(mode)
            facts.append(dict(path=name, sha256=digest, bytes=info.file_size, mode=mode))
        else:
            # No link exists until all regular members have been written.
            import io
            output = io.BytesIO()
            read_member(archive, info, output)
            value = output.getvalue().decode('utf-8', 'strict')
            require(value and not value.startswith('/') and '\\' not in value and
                    not any(ord(c) < 32 or ord(c) == 127 for c in value), 'ZIP contains an unsafe link')
            links[name] = value
    for name, value in links.items():
        os.symlink(value, stage / name)
        facts.append(dict(path=name, target=value))
    for name in links:
        try:
            resolved = (stage / name).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError('ZIP contains a dangling or cyclic link') from exc
        require(resolved.is_relative_to(stage), 'ZIP link escapes the payload')
    # Apply directory modes last, so a read-only directory cannot block staging.
    for name, kind, mode, _ in sorted(rows, reverse=True):
        if kind == stat.S_IFDIR:
            (stage / name).chmod(mode)
    return facts


def inspect_payload(stage, target, elf, targets):
    machine = targets.target_definition(target)['elf']
    for name in ('electron', 'LICENSE', 'LICENSES.chromium.html', 'version'):
        path = stage / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
                'runtime lacks a regular required member: ' + name)
    require((stage / 'version').stat().st_size <= 64 and
            (stage / 'version').read_bytes() in (VERSION, VERSION + b'\n'), 'Electron version differs')
    require((stage / 'electron').stat().st_mode & 0o111, 'Electron is not executable')
    images = []
    for path in sorted(stage.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        header = elf.read_elf_header(path, machine=machine)
        if header is not None:
            require(header['class'] == 64 and header['type'] in (2, 3), 'runtime contains a non-runtime ELF')
            images.append(dict(path=path.relative_to(stage).as_posix(), **elf.read_elf_dynamic(path, machine=machine)))
        elif path.stat().st_mode & 0o111:
            with path.open('rb') as source:
                magic = source.read(4)
            require(magic not in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf',
                                 b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xce',
                                 b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
                                 b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca') and
                    not magic.startswith(b'MZ'), 'runtime contains a foreign executable')
    require(any(row['path'] == 'electron' for row in images), 'Electron is not a target ELF executable')
    return images


def stage_runtime(archive_path, destination, *, archive_sha256, target, sdk):
    """Extract bytes to a new owned work directory; return facts, not acceptance.

    The caller holds its input and destination-parent locks. This function does
    not run payloads, write a package receipt, or validate a build/sysroot/loader.
    """
    paths, publication, elf, targets = sdk
    require(isinstance(archive_sha256, str) and re.fullmatch('[0-9a-f]{64}', archive_sha256),
            'an exact archive SHA256 is required')
    destination = Path(paths.canonical_new(destination))
    paths.real_directory(destination.parent)
    paths.reject_overlap(archive_path, destination)
    require(not os.path.lexists(destination), 'staging destination already exists')
    publication.require_directory_publication()
    handle, before = paths.open_regular(archive_path)
    with handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        require(digest == archive_sha256, 'ZIP SHA256 differs')
        check_zip_directory(handle, before.st_size)
        with zipfile.ZipFile(handle) as archive, tempfile.TemporaryDirectory(
                prefix='.electron-stage-', dir=destination.parent) as temporary:
            stage = Path(temporary)
            facts = extract(archive, stage, zip_members(archive))
            images = inspect_payload(stage, target, elf, targets)
            paths.verify_stable(archive_path, before)
            publication.publish_directory_noreplace(stage, destination)
    return dict(archive_sha256=digest, members=facts, elf=images)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--archive-sha256', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--target', required=True, choices=('amd64', 'aarch64'))
    args = parser.parse_args()
    print(json.dumps(stage_runtime(args.archive, args.destination, archive_sha256=args.archive_sha256,
                                  target=args.target, sdk=load_sdk(args.sdk_source)), indent=2))


if __name__ == '__main__':
    main()
