#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Qualify the installed base libelf provider selected by Mesa's RadeonSI."""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import re
import sys


ARCH_MACHINES = {'x86_64': 62, 'aarch64': 183}
HEADER_MAP = {
    'libelf/libelf.h': 'usr/include/libelf.h',
    'libelf/gelf.h': 'usr/include/gelf.h',
    'common/elfdefinitions.h': 'usr/include/elfdefinitions.h',
}
ARCHIVE_NAME = 'libelf.a'
SHARED_NAME = 'libelf.so.2.0'
SONAME = 'libelf.so.2'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def regular_bytes(path, label):
    require(path.is_file() and not path.is_symlink(), f'{label} is not a regular file: {path}')
    return path.read_bytes()


def source_manifest(recipe):
    manifest_path = recipe / 'files/base-source.json'
    manifest = json.loads(regular_bytes(manifest_path, 'base source manifest'))
    require(manifest.get('format') == 'emberbsd-elftoolchain-base-source' and
            manifest.get('version') == 1, 'unsupported base source manifest')
    upstream = manifest.get('upstream')
    require(isinstance(upstream, dict) and isinstance(upstream.get('distname'), str),
            'base source manifest has no upstream identity')
    archive = upstream.get('archive')
    require(isinstance(archive, dict) and type(archive.get('size')) is int and
            re.fullmatch(r'[0-9a-f]{64}', archive.get('sha256', '')) and
            re.fullmatch(r'[0-9a-f]{128}', archive.get('sha512', '')) and
            re.fullmatch(r'[0-9a-f]{64}', archive.get('blake2s', '')),
            'base source manifest has invalid archive checksums')
    files = manifest.get('files')
    require(isinstance(files, dict), 'base source manifest has no file map')
    for name in HEADER_MAP:
        entry = files.get(name)
        require(isinstance(entry, dict) and type(entry.get('size')) is int and
                re.fullmatch(r'[0-9a-f]{64}', entry.get('sha256', '')),
                f'base source manifest has no canonical header: {name}')
    return manifest


def validate_distinfo(recipe, manifest):
    data = regular_bytes(recipe / 'distinfo', 'canonical distinfo')
    try:
        text = data.decode('ascii')
    except UnicodeError as exc:
        raise ValueError('canonical distinfo is not ASCII') from exc
    records = {}
    pattern = re.compile(r'(BLAKE2s|SHA512|Size|SHA1) \(([^/()]+)\) = ([0-9a-f]+)( bytes)?')
    for line in text.splitlines():
        if not line or line.startswith('$NetBSD:'):
            continue
        match = pattern.fullmatch(line)
        require(match is not None, f'unrecognized distinfo entry: {line!r}')
        kind, name, value, suffix = match.groups()
        require((kind == 'Size') == (suffix == ' bytes') and (kind, name) not in records,
                'invalid or duplicate distinfo entry')
        records[kind, name] = value

    upstream = manifest['upstream']
    archive_name = upstream['distname'] + '.tar.bz2'
    archive = upstream['archive']
    expected = {
        ('BLAKE2s', archive_name): archive['blake2s'],
        ('SHA512', archive_name): archive['sha512'],
        ('Size', archive_name): str(archive['size']),
    }
    require(all(records.get(key) == value for key, value in expected.items()),
            'canonical distinfo does not match the base source archive')

    patches_dir = recipe / 'patches'
    require(patches_dir.is_dir(), 'base recipe has no patches directory')
    patches = sorted(p for p in patches_dir.iterdir() if p.is_file())
    require(all(not p.is_symlink() for p in patches), 'base recipe contains a patch symlink')
    expected_keys = set(expected) | {('SHA1', patch.name) for patch in patches}
    require(set(records) == expected_keys, 'canonical distinfo does not cover exactly the archive and patches')
    for patch in patches:
        filtered = b''.join(line for line in patch.read_bytes().splitlines(keepends=True)
                            if b'$NetBSD' not in line)
        require(hashlib.sha1(filtered).hexdigest() == records['SHA1', patch.name],
                f'canonical patch checksum mismatch: {patch.name}')
    return data, manifest


def load_elf_api(recipe, sdk_source):
    pkgsrc_root = recipe.parent.parent
    loader_path = pkgsrc_root / 'lang/llvm/files/sdk_source.py'
    require(loader_path.is_file(), f'missing shared SDK source selector: {loader_path}')
    spec = importlib.util.spec_from_file_location('_mesa_sdk_source', loader_path)
    require(spec is not None and spec.loader is not None, 'cannot load shared SDK source selector')
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    selected, remaining = loader.load_sdk(['--sdk-source', str(sdk_source)])
    require(not remaining, 'unexpected SDK selector arguments')
    sdk_package = Path(selected) / 'src/emberbsd_sdk'
    api = importlib.import_module('emberbsd_sdk.elf')
    require(Path(api.__file__).resolve().is_relative_to(sdk_package.resolve()) and
            callable(getattr(api, 'read_elf_dynamic', None)) and
            callable(getattr(api, 'read_archive', None)),
            'selected SDK lacks the required ELF API1 readers')
    return api


def check_buildlink(buildlink):
    names = {'libelf.h', 'gelf.h', 'elfdefinitions.h', 'libelf.a',
             'libelf.so', 'libelf.so.2', 'libelf.so.2.0', 'libelf.pc'}
    locations = ('include', 'include/sys', 'lib', 'lib64',
                 'lib/pkgconfig', 'lib64/pkgconfig', 'share/pkgconfig')
    found = []
    for relative in locations:
        directory = buildlink / relative
        if not directory.is_dir():
            continue
        for child in directory.iterdir():
            if child.name in names or child.name.startswith('libelf.so.'):
                found.append(str(child))
    require(not found, 'package buildlink supplies libelf: ' + ', '.join(sorted(found)))


def rooted_path(root, relative, *, regular=False):
    path = root / relative
    require(path.exists() or path.is_symlink(), f'missing target file: {relative}')
    resolved = path.resolve(strict=True)
    require(resolved.is_relative_to(root), f'target path escapes selected root: {relative}')
    if regular:
        require(path.is_file() and not path.is_symlink(), f'target file is not regular: {relative}')
    return path


def check_target(root, manifest, distinfo, elf_api, machine):
    marker = rooted_path(root, 'usr/share/emberbsd/ports/elftoolchain.distinfo', regular=True)
    require(regular_bytes(marker, 'installed base-source marker') == distinfo,
            'installed base-source marker differs from canonical Ports distinfo')

    for source_name, target_name in HEADER_MAP.items():
        target = rooted_path(root, target_name, regular=True)
        data = regular_bytes(target, target_name)
        expected = manifest['files'][source_name]
        require(len(data) == expected['size'] and sha256(data) == expected['sha256'],
                f'target header differs from canonical base source: {target_name}')

    definitions = rooted_path(root, 'usr/include/sys/elfdefinitions.h', regular=True)
    definition_data = regular_bytes(definitions, 'target ELF definitions')
    for name, value in (('ELFCLASS32', '1'), ('ELFCLASS64', '2'), ('ELFDATA2LSB', '1')):
        pattern = (rb'^\s*#\s*define\s+' + name.encode('ascii') +
                   rb'\s+' + value.encode('ascii') + rb'U?\b')
        require(re.search(pattern, definition_data, re.M) is not None,
                f'target ELF definitions have the wrong {name}')

    shared = rooted_path(root, 'usr/lib/' + SHARED_NAME, regular=True)
    dynamic = elf_api.read_elf_dynamic(shared, machine=machine)
    require(dynamic.get('class') == 64 and dynamic.get('endian') == 'little' and
            dynamic.get('type') == 3 and dynamic.get('soname') == SONAME,
            'base shared libelf has the wrong ELF class, type, endian, or SONAME')
    for alias in ('usr/lib/libelf.so.2', 'usr/lib/libelf.so'):
        path = rooted_path(root, alias)
        require(path.is_symlink() and path.resolve(strict=True) == shared.resolve(strict=True),
                f'base libelf alias does not resolve to {SHARED_NAME}: {alias}')

    archive = rooted_path(root, 'usr/lib/' + ARCHIVE_NAME, regular=True)
    archive_info = elf_api.read_archive(archive, machine)
    require(type(archive_info.get('elf_members')) is int and archive_info['elf_members'] > 0,
            'base static libelf has no target ELF members')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-recipe', required=True, type=Path)
    parser.add_argument('--sdk-source', required=True, type=Path)
    parser.add_argument('--target-root', required=True, type=Path)
    parser.add_argument('--buildlink-dir', required=True, type=Path)
    parser.add_argument('--mode', choices=('native', 'cross'), required=True)
    parser.add_argument('--arch', choices=tuple(ARCH_MACHINES), required=True)
    args = parser.parse_args()
    try:
        for name in ('base_recipe', 'sdk_source', 'target_root', 'buildlink_dir'):
            value = getattr(args, name)
            require(value.is_absolute(), f'--{name.replace("_", "-")} must be absolute')
        recipe = args.base_recipe.resolve(strict=True)
        sdk_source = args.sdk_source.resolve(strict=True)
        target_root = args.target_root.resolve(strict=True)
        buildlink = args.buildlink_dir.resolve(strict=True)
        require((recipe / 'Makefile').is_file() and (recipe / 'distinfo').is_file(),
                'base recipe is incomplete')
        require(buildlink.is_dir(), 'buildlink directory does not exist')
        require(buildlink != Path('/') and buildlink != target_root,
                'buildlink directory must be separate from the selected target root')
        if args.mode == 'native':
            require(target_root == Path('/'), 'native mode must select the host target root /')
        else:
            require(target_root != Path('/'), 'cross mode must select CROSS_DESTDIR, never host root /')
        manifest = source_manifest(recipe)
        distinfo, manifest = validate_distinfo(recipe, manifest)
        elf_api = load_elf_api(recipe, sdk_source)
        check_buildlink(buildlink)
        check_target(target_root, manifest, distinfo, elf_api, ARCH_MACHINES[args.arch])
        print(f'PASS: {args.mode} base libelf provider for {args.arch}; no package buildlink')
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
