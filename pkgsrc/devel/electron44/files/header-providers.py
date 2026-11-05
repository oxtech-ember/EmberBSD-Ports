#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select installed, common target headers for the Electron source view."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

# Each prefix is relative to the installed /usr/pkg; destinations are GN paths.
PROVIDERS = {
    'eigen3': ('math/eigen3', 'eigen3>=5.0.1', 'include/eigen3',
               'third_party/eigen3/src', ('include/eigen3/Eigen/Core',)),
    'flatbuffers': ('devel/flatbuffers', 'flatbuffers>=25.12.19.1',
                    'include/flatbuffers', 'third_party/flatbuffers/src/include/flatbuffers',
                    ('include/flatbuffers/flatbuffers.h',)),
    'fp16': ('devel/fp16', 'fp16>=0.0.0pre20260620', 'include',
             'third_party/fp16/src/include', ('include/fp16.h', 'include/fp16/fp16.h')),
}


def select(options, sdk, native, env, *, source_check):
    """Return pkgdb-owned files; the source-view owner handles content fingerprints.

    source_check is the common package source metadata verifier supplied by the
    controller. No tree is copied or hashed here and no SDK cache is duplicated.
    """
    del native
    prefix = (Path(options.sysroot) / 'usr/pkg').resolve(strict=True)
    db = (prefix / 'pkgdb').resolve(strict=True)
    host = Path(options.host_prefix).resolve(strict=True)
    pkg_info = (host / 'sbin/pkg_info').resolve(strict=True)
    if not db.is_relative_to(prefix) or not pkg_info.is_relative_to(host):
        raise ValueError('package inspector or database escapes the selected prefix')
    selected = {}
    for name, (pkgpath, pattern, subtree, destination, required) in PROVIDERS.items():
        output = sdk['process'].capture([str(pkg_info), '-K', str(db), '-E', pattern], env=env).stdout.decode('utf-8', 'strict')
        names = output.splitlines()
        if len(names) != 1 or '/' in names[0] or names[0] in ('.', '..'):
            raise ValueError('ambiguous selected header provider: ' + name)
        package = (db / names[0]).resolve(strict=True)
        if package.parent != db:
            raise ValueError('header package escapes selected pkgdb')
        info = (package / '+BUILD_INFO').read_text().splitlines()
        if 'PKGPATH=' + pkgpath not in info:
            raise ValueError('header package owner differs: ' + name)
        exported = Path(options.host_buildlink_pkgsrc) / pkgpath
        owner = Path(options.ports_source) / 'pkgsrc' / pkgpath
        if not owner.is_dir():
            owner = exported
        source_check(package, owner, exported, distinfo=True, package_path=pkgpath,
                     allow_empty_patches=True)
        manifest = (package / '+CONTENTS').read_text().splitlines()
        checksums = {}
        for index, line in enumerate(manifest[:-1]):
            if line.startswith('@'):
                continue
            match = re.fullmatch(r'@comment MD5:([0-9a-f]{32})', manifest[index + 1])
            if match:
                if line in checksums:
                    raise ValueError('duplicate package checksum: ' + line)
                checksums[line] = match.group(1)
        raw = sdk['process'].capture([str(pkg_info), '-K', str(db), '-qL', names[0]], env=env).stdout.decode('utf-8', 'strict')
        records = []
        for line in raw.splitlines():
            logical = PurePosixPath(line)
            if not logical.is_absolute() or '..' in logical.parts:
                raise ValueError('unsafe package path: ' + line)
            try:
                relative = logical.relative_to('/usr/pkg').as_posix()
            except ValueError:
                raise ValueError('package path outside selected prefix: ' + line)
            include = (relative == 'include/fp16.h' or relative.startswith('include/fp16/')) if name == 'fp16' else relative.startswith(subtree + '/')
            if not include:
                continue
            path = prefix / relative
            actual = path.resolve(strict=True)
            if not actual.is_relative_to(prefix) or not actual.is_file():
                raise ValueError('selected header escapes prefix or is not a file: ' + relative)
            records.append(relative)
        if len(records) != len(set(records)) or not set(required).issubset(records):
            raise ValueError('incomplete or duplicate owned headers: ' + name)
        records.sort()
        if not set(records).issubset(checksums):
            raise ValueError('selected header lacks package checksum: ' + name)
        stable = {}
        for relative in records:
            path = prefix / relative
            info = sdk['paths'].regular_file(path)
            stable[relative] = list(sdk['paths'].stable_identity(info))
            sdk['paths'].verify_stable(path, info)
        expected_md5 = {relative: checksums[relative] for relative in records}
        metadata = {item: hashlib.sha256((package / item).read_bytes()).hexdigest()
                    for item in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')}
        identity = hashlib.sha256(json.dumps({'pkgpath': pkgpath, 'package': names[0],
                                              'metadata': metadata, 'files': records,
                                              'stable': stable, 'expected_md5': expected_md5},
                                             sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        selected[name] = {'root': str(prefix / subtree), 'destination': destination,
                          'identity': identity, 'files': records, 'package': str(package),
                          'expected_md5': expected_md5, 'stable': stable}
    return selected
