# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Verify an existing target compiler-rt package against its staged resources."""
import hashlib
import os
from pathlib import Path
import re
import tarfile


def bind(record, resource, compiler_include):
    """Keep application runtime headers/flags and add link-only sanitizer runtime."""
    include = '-isystem'
    for role in ('cc', 'cxx', 'cpp'):
        words = record['commands'][role]
        # Preserve the SDK-selected C++ headers and place the sanitizer-only
        # include root before the host Clang builtin resource headers.
        index = next(i for i, word in enumerate(words)
                     if word == '-isystem' and i + 1 < len(words)
                     and words[i + 1] == compiler_include)
        words[index:index] = [include, str(resource / 'include')]
    for role in ('cc', 'cxx'):
        record['link_flags'][role].append('-resource-dir=' + str(resource))
    return record


def verify(package, expected_sha256, resource, sdk, *, version, target):
    package = Path(package)
    resource = Path(resource)
    if target != 'amd64' or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('diagnostic sanitizer target/compiler is not supported')
    if not re.fullmatch('[0-9a-f]{64}', expected_sha256 or ''):
        raise ValueError('exact sanitizer package digest required')
    if not package.is_absolute() or package.is_symlink() or not package.is_file():
        raise ValueError('invalid sanitizer package')
    if not resource.is_absolute() or resource.is_symlink() or not resource.is_dir():
        raise ValueError('invalid sanitizer resource')
    handle, before = sdk['paths'].open_regular(package)
    with handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    sdk['paths'].verify_stable(package, before)
    before_package = before
    if digest != expected_sha256:
        raise ValueError('sanitizer package digest differs')
    if not re.fullmatch(r'compiler-rt-' + re.escape(version) + r'(?:nb[0-9]+)?', sdk['package_updates']._archive(package)['name']):
        raise ValueError('sanitizer package identity differs')
    sdk['binary_release'].inspect_package(package, {'arch': 'x86_64'})
    if resource.name != version.split('.')[0]:
        raise ValueError('sanitizer resource version differs')
    prefix = 'lib/clang/' + version.split('.')[0] + '/'
    wanted = set()
    build_version = None
    with package.open('rb') as stream, tarfile.open(fileobj=sdk['binary_release']._package_payload(stream), mode='r|*') as archive:
        for member in archive:
            name = member.name.removeprefix('./')
            if name == '+BUILD_VERSION':
                if build_version is not None or not member.isfile() or member.size > 8 * 1024 * 1024:
                    raise ValueError('invalid sanitizer package source metadata')
                build_version = archive.extractfile(member).read().decode('utf-8')
                continue
            if not name.startswith(prefix):
                continue
            rel = name[len(prefix):]
            if member.isdir():
                continue
            if not member.isfile() or rel in wanted or '..' in Path(rel).parts:
                raise ValueError('invalid sanitizer package member')
            path = resource / rel
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(resource.resolve()):
                raise ValueError('sanitizer staged member missing or unsafe: ' + rel)
            handle, before = sdk['paths'].open_regular(path)
            with handle:
                staged = hashlib.file_digest(handle, 'sha256').digest()
            sdk['paths'].verify_stable(path, before)
            if hashlib.file_digest(archive.extractfile(member), 'sha256').digest() != staged:
                raise ValueError('sanitizer staged member differs: ' + rel)
            wanted.add(rel)
    required = {'include/sanitizer/asan_interface.h', 'include/sanitizer/ubsan_interface.h',
                'lib/netbsd/libclang_rt.asan-x86_64.a', 'lib/netbsd/libclang_rt.asan_static-x86_64.a',
                'lib/netbsd/libclang_rt.asan_cxx-x86_64.a', 'lib/netbsd/libclang_rt.ubsan_standalone-x86_64.a',
                'lib/netbsd/libclang_rt.ubsan_standalone_cxx-x86_64.a'}
    sdk['paths'].verify_stable(package, before_package)
    found, found_dirs = set(), set()
    for current, dirs, files in os.walk(resource, followlinks=False):
        for name in dirs + files:
            path = Path(current) / name
            if path.is_symlink():
                raise ValueError('symlink in sanitizer resource: ' + str(path))
            if name in dirs:
                found_dirs.add(path.relative_to(resource).as_posix())
            if name in files:
                if not path.is_file():
                    raise ValueError('nonregular sanitizer resource: ' + str(path))
                found.add(path.relative_to(resource).as_posix())
    expected_dirs = {str(parent) for name in wanted for parent in Path(name).parents if str(parent) != '.'}
    if found != wanted or found_dirs != expected_dirs:
        raise ValueError('sanitizer resource contains missing or extra files')
    if not build_version:
        raise ValueError('missing sanitizer package source metadata')
    if not required <= wanted:
        raise ValueError('sanitizer package is incomplete')
    for rel in sorted(required):
        if rel.endswith('.a') and sdk['elf'].read_archive(resource / rel, 62)['elf_members'] == 0:
            raise ValueError('sanitizer archive has no target objects: ' + rel)
    return resource.resolve(), build_version
