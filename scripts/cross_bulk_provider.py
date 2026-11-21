#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors.
"""Fingerprint the installed providers used by pkgsrc's resolved dependency list."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import sys


def digest(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True).encode()


class UnclassifiedProvider(ValueError):
    """Registration does not support comparison across package versions."""


def package_interface(name, contents, build, inspect_elf, *, inspect_file, inspect_link):
    """Compare all registered file bytes, modes, links and installation metadata.

    Callbacks inspect actual files at the registered path and validate their
    recorded checksums or link targets. The ELF callback also verifies its magic.
    """
    base, separator, version = name.rpartition('-')
    if not base or not separator or not re.fullmatch(r'[0-9][A-Za-z0-9._+~]*', version):
        raise UnclassifiedProvider('unknown package base/version')
    lines = contents.decode().splitlines()
    if [line for line in lines if line.startswith('@name ')] != ['@name ' + name]:
        raise ValueError('different provider identity')
    cwd = sorted({line[5:] for line in lines if line.startswith('@cwd ')})
    if len(cwd) != 1 or not Path(cwd[0]).is_absolute():
        raise UnclassifiedProvider('nonstandard installed prefix')
    for field in ('PKGPATH', 'MACHINE_ARCH', 'OPSYS', 'LOCALBASE'):
        values = re.findall(r'^' + field + r'=(.+)$', build, re.M)
        if len(values) != 1 or (field == 'LOCALBASE' and values[0] != cwd[0]):
            raise UnclassifiedProvider('missing or inconsistent provider ' + field)
    providers = set(re.findall(r'^PROVIDES=(.+)$', build, re.M))
    if not providers:
        raise UnclassifiedProvider('no declared shared library')
    records = []
    count = 0
    for i, item in enumerate(lines):
        if i and lines[i - 1] == '@ignore':
            if item not in ('+COMMENT', '+DESC', '+BUILD_VERSION', '+BUILD_INFO', '+SIZE_PKG', '+SIZE_ALL',
                            '+DISPLAY', '+MTREE_DIRS', '+INSTALL', '+DEINSTALL'):
                raise UnclassifiedProvider('unclassified ignored package file')
            if item in ('+INSTALL', '+DEINSTALL'):
                raise UnclassifiedProvider('installation scripts can change provider contents')
            continue
        if item.startswith(('@name ', '@blddep ')):
            continue
        if item.startswith('@'):
            if item != '@ignore' and not item.startswith(('@cwd ', '@pkgdep ', '@comment ')):
                raise UnclassifiedProvider('unclassified package directive')
            if not item.startswith(('@comment MD5:', '@comment Symlink:')):
                records.append(item)
            continue
        relative = PurePosixPath(item)
        if relative.is_absolute() or '..' in relative.parts or i + 1 == len(lines):
            raise UnclassifiedProvider('unsupported package file entry')
        checksum = lines[i + 1]
        if checksum.startswith('@comment Symlink:'):
            inspect_link(relative, checksum.removeprefix('@comment Symlink:'))
            records.append((item, checksum))
            continue
        if not re.fullmatch(r'@comment MD5:[0-9a-f]{32}', checksum):
            raise UnclassifiedProvider('package file has no recorded checksum')
        if re.search(r'\.so\.\d+(?:\.\d+)*$', item) and str(PurePosixPath(cwd[0]) / relative) in providers:
            records.append((item, inspect_elf(relative, checksum.removeprefix('@comment MD5:'))))
            count += 1
        else:
            # Includes all headers, static archives, pkg-config, CMake files
            # and executables. Without link evidence, a changed .a blocks reuse.
            identity = inspect_file(relative, checksum.removeprefix('@comment MD5:'))
            records.append((item, identity))
    if not count:
        raise UnclassifiedProvider('no supported versioned ELF')
    abi = [line for line in build.splitlines() if line.startswith(
        ('ABI=', 'LOCALBASE=', 'OPSYS=', 'OS_VERSION=', 'MACHINE_ARCH=', 'OBJECT_FMT=', 'PKGPATH=', 'PROVIDES=', 'REQUIRES='))]
    return [base, digest(encoded([records, sorted(abi)]))]


def installed_stamps(prefix, contents):
    """Bind a per-pass memo to the actual file identities in this installation."""
    stamps = []
    ignored = False
    for line in contents.decode().splitlines():
        if ignored:
            ignored = False
            continue
        if line == '@ignore':
            ignored = True
        if line.startswith('@'):
            continue
        relative = PurePosixPath(line)
        if relative.is_absolute() or '..' in relative.parts:
            raise UnclassifiedProvider('unsafe registered path')
        path = prefix / relative
        if not path.parent.resolve(strict=True).is_relative_to(prefix):
            raise UnclassifiedProvider('registered path outside installed prefix')
        status = path.lstat()
        stamps.append((line, status.st_dev, status.st_ino, status.st_mode, status.st_size,
                       status.st_mtime_ns, status.st_ctime_ns))
    return stamps


def provider_key(resolved, target_db, host_db, native=False, cache=None):
    rows = []
    memo = {}
    for row in resolved.read_text().splitlines():
        kind, pattern, name = row.split()
        if kind not in ('bootstrap', 'tool', 'build', 'full', 'indirect-build', 'indirect-full', 'test') or not re.fullmatch(r'[A-Za-z0-9_+.,@%-][A-Za-z0-9_+.,@%-]*', name):
            raise ValueError('invalid resolved provider')
        host = native or kind in ('bootstrap', 'tool')
        db = host_db if host else target_db
        if not db.is_absolute():
            raise ValueError('missing selected pkgdb')
        key = (db, name, kind)
        if key not in memo:
            contents = (db / name / '+CONTENTS').read_bytes()
            build = (db / name / '+BUILD_INFO').read_bytes()
            if b'@name ' + name.encode() not in contents.splitlines():
                raise ValueError('installed provider has a different name')
            identity = [name, digest(contents), digest(build)]
            if not host and kind in ('full', 'indirect-full') and db.name == 'pkgdb':
                prefix = db.parent.resolve(strict=True)
                def inspect_file(relative, expected_md5, *, elf=False):
                    path = prefix / relative
                    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(prefix) or not path.is_file():
                        raise ValueError('unknown installed file location')
                    md5, sha = hashlib.md5(), hashlib.sha256()
                    with path.open('rb') as stream:
                        magic = stream.read(4)
                        if elf and magic != b'\x7fELF':
                            raise ValueError('declared versioned library is not ELF')
                        md5.update(magic)
                        sha.update(magic)
                        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                            md5.update(chunk)
                            sha.update(chunk)
                    if md5.hexdigest() != expected_md5:
                        raise ValueError('installed file differs from registered package')
                    return [sha.hexdigest(), os.stat(path).st_mode & 0o7777]
                def inspect_elf(relative, expected_md5):
                    return inspect_file(relative, expected_md5, elf=True)
                def inspect_link(relative, target):
                    path = prefix / relative
                    if not path.parent.resolve(strict=True).is_relative_to(prefix) or os.readlink(path) != target:
                        raise ValueError('installed symlink differs from registered package')
                try:
                    memo_file = None
                    stamps = installed_stamps(prefix, contents)
                    if cache is not None:
                        key_data = [str(prefix), identity, stamps]
                        memo_file = cache / digest(encoded(key_data))
                    if memo_file is not None and memo_file.is_file():
                        candidate = json.loads(memo_file.read_text())
                    else:
                        candidate = package_interface(name, contents, build.decode(), inspect_elf,
                                                      inspect_file=inspect_file, inspect_link=inspect_link)
                        if stamps != installed_stamps(prefix, contents):
                            raise ValueError('provider changed during input inspection')
                        if memo_file is not None:
                            cache.mkdir(exist_ok=True)
                            with tempfile.NamedTemporaryFile(mode='w', dir=cache, delete=False) as stream:
                                json.dump(candidate, stream)
                            os.replace(stream.name, memo_file)
                    identity = candidate
                except UnclassifiedProvider:
                    pass  # Unsupported manifests use exact identity. Corruption is an error.
            memo[key] = identity
        # The resolver owns version patterns; archive validation compares
        # the required @pkgdep separately from the consumed provider files.
        rows.append(encoded([kind, memo[key]]))
    return digest(b'\n'.join(sorted(set(rows))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resolved', type=Path)
    parser.add_argument('target_db', type=Path)
    parser.add_argument('host_db', type=Path)
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--cache', type=Path)
    args = parser.parse_args()
    try:
        print(provider_key(args.resolved, args.target_db, args.host_db, args.native, args.cache))
    except (OSError, ValueError) as error:
        sys.exit(str(error))
