#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted migration of prepare-pkgsrc.sh.
"""Export the complete pinned pkgsrc tree through explicitly selected tools."""

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile

sys.dont_write_bytecode = True


class ExportError(ValueError):
    """An input cannot produce the canonical export."""


def require(value, message):
    if not value:
        raise ExportError(message)


def joined(root, relative):
    # Shell "$root/$relative" does not discard root for a leading slash.
    return Path(str(root) + '/' + relative)


def destination_path(value):
    value = os.fspath(value)
    require(value.startswith('/'), 'Destination must be absolute.')
    require(re.fullmatch(r'[a-zA-Z0-9_./-]+', value),
            'pkgsrc requires a path without whitespace or shell metacharacters.')
    path = Path(value)
    require(not os.path.lexists(path), 'Destination already exists.')
    return path


def patch_sha1(path):
    raw = path.read_bytes()
    chunks = raw.split(b'\n')
    filtered = b''.join(line + (b'\n' if index < len(chunks) - 1 else b'')
                        for index, line in enumerate(chunks) if b'$NetBSD' not in line)
    return hashlib.sha1(filtered).hexdigest()


def check_recipe(source, label, root):
    require((source / 'Makefile').is_file(), f'Incomplete recipe: {label} has no Makefile.')
    declared = {}
    if (source / 'distinfo').is_file():
        for line in (source / 'distinfo').read_bytes().splitlines():
            fields = line.split()
            if len(fields) >= 4 and fields[0] == b'SHA1' and fields[1].startswith(b'(patch-'):
                name = fields[1].replace(b'(', b'').replace(b')', b'').decode('utf-8')
                path = source / 'patches' / name
                require(path.is_file(), f'Missing patch: {label}/patches/{name}')
                require(fields[3].decode('ascii') == patch_sha1(path),
                        f'Patch checksum differs: {label}/patches/{name}')
                declared[name] = True
    for path in (source / 'patches').glob('patch-*'):
        require(path.name in declared, f'Undeclared patch: {label}/patches/{path.name}')
    for directory, dirs, files in os.walk(source, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            if not path.is_symlink():
                continue
            target = os.readlink(path)
            require(not os.path.isabs(target), f'Link leaves the repository: {path}')
            lexical = Path(os.path.abspath(path.parent / target))
            require(lexical.is_relative_to(root), f'Link leaves the repository: {path}')
            try:
                resolved = path.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                raise ExportError(f'Broken link: {path}') from error
            require(resolved.is_relative_to(root), f'Link leaves the repository: {path}')
            require(resolved.is_file(), f'Broken link: {path}')


def configuration(root):
    config = root / 'pkgsrc/export.conf'
    require(config.is_file(), 'Missing pkgsrc/export.conf.')
    recipes, patches, files = [], [], []
    # POSIX read with tab IFS collapses adjacent tabs. It ignores an unfinished
    # final record. Preserve this input grammar during the migration.
    for raw in config.read_bytes().decode('utf-8').split('\n')[:-1]:
        fields = re.split(r'\t+', raw.strip('\t'))
        method = fields[0]
        if not method or method.startswith('#'):
            continue
        require(len(fields) <= 4, f'pkgsrc/export.conf: too many fields for {method}.')
        first, second, third = (fields[1:] + ['', '', ''])[:3]
        source = joined(root, first)
        if method == 'recipe':
            require(second and not third, 'pkgsrc/export.conf: use recipe SOURCE PKGPATH.')
            check_recipe(source, first, root)
            recipes.append((second, source))
        elif method == 'patch':
            require(not second, 'pkgsrc/export.conf: use patch FILE.')
            require(source.is_file() and source.stat().st_size, f'Missing infrastructure patch: {first}')
            patches.append((method, source, '', ''))
        elif method == 'git-apply':
            require(second and not third, 'pkgsrc/export.conf: use git-apply FILE MANIFEST.')
            require(source.is_file() and source.stat().st_size, f'Missing infrastructure patch: {first}')
            recorded = [line.split('\t')[1] for line in joined(root, second).read_bytes().decode('utf-8').split('\n')
                        if line.split('\t')[0] == source.name and len(line.split('\t')) > 1]
            require(recorded == [hashlib.sha256(source.read_bytes()).hexdigest()],
                    f'Infrastructure patch differs from {second}: {first}')
            patches.append((method, source, '', ''))
        elif method == 'recipe-patch':
            require(third, 'pkgsrc/export.conf: use recipe-patch FILE PKGPATH NAME.')
            require(source.is_file() and source.stat().st_size, f'Missing recipe patch: {first}')
            require(third.startswith('patch-'), f'Recipe patch names start with patch-: {third}')
            patches.append((method, source, second, third))
        elif method == 'file':
            require(second and not third, 'pkgsrc/export.conf: use file SOURCE DESTINATION.')
            require(source.is_file(), f'Missing exported file: {first}')
            files.append((source, second))
        else:
            raise ExportError(f'pkgsrc/export.conf: unknown method {method}.')
    categories = sorted(path for path in (root / 'pkgsrc').iterdir()
                        if path.is_dir() and not path.name.startswith('.'))
    for category in categories:
        for package in sorted(path for path in category.iterdir()
                              if path.is_dir() and not path.name.startswith('.')):
            name = category.name + '/' + package.name
            check_recipe(package, 'pkgsrc/' + name, root)
            recipes.append((name, package))
    names = [name for name, source in recipes]
    duplicate = next((name for name in sorted(names) if names.count(name) > 1), None)
    require(duplicate is None, f'Two recipe sources provide {duplicate}.')
    return recipes, patches, files, categories


def copy_file(source, target):
    source, target = Path(source), Path(target)
    shutil.copyfile(source, target)
    os.chmod(target, stat.S_IMODE(source.stat().st_mode) & ~0o022)


def extract_archive(archive, destination):
    with tarfile.open(archive, 'r:') as stream:
        members = stream.getmembers()
        names = set()
        links = set()
        for member in members:
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and '..' not in name.parts and name.parts,
                    'Unsafe Git archive member: ' + member.name)
            require(name not in names, 'Duplicate Git archive member: ' + member.name)
            require(member.isdir() or member.isfile() or member.issym() or member.islnk(),
                    'Unsupported Git archive member: ' + member.name)
            # tar -xf without -p applies the exporter's umask 022. Python's
            # fully_trusted filter otherwise restores Git archive group-write.
            member.mode &= ~0o022
            names.add(name)
            if member.issym():
                links.add(name)
            if member.islnk():
                target = PurePosixPath(member.linkname)
                require(not target.is_absolute() and '..' not in target.parts,
                        'Unsafe Git archive hard link: ' + member.name)
        require(all(not any(parent in links for parent in name.parents) for name in names),
                'Git archive writes through a symbolic link.')
        regulars = {PurePosixPath(member.name) for member in members if member.isfile()}
        require(all(not member.islnk() or PurePosixPath(member.linkname) in regulars
                    for member in members), 'Git archive hard link has no regular member target.')
        # Git symlinks are data. The complete roster check above prevents writes
        # through them. Do not use Python's changing default extraction filter.
        stream.extractall(destination, members=members, filter='fully_trusted')


def export_pkgsrc(root, destination, *, selection, runner, scratch):
    """Export once. Return the upstream revision. The caller owns SDK leases.

    selection is an admitted SDK API1 selection. runner(argv, cwd=None,
    input=None) returns captured bytes or raises the real child status.
    scratch is a new absolute caller-owned work child. This function never
    removes it. The caller holds its work lease and cleans only after proven
    child drainage. Retain scratch and leases on SDK ProcessOwnershipError.
    This function neither qualifies tools nor searches PATH.
    """
    root = Path(root).resolve(strict=True)
    destination = destination_path(destination)
    scratch = destination_path(scratch)
    require(scratch != destination and not scratch.is_relative_to(destination)
            and not destination.is_relative_to(scratch), 'Scratch overlaps the destination.')
    require(not scratch.is_relative_to(root) and not root.is_relative_to(scratch),
            'Scratch overlaps the Ports source.')
    recipes, patches, files, categories = configuration(root)

    def invoke(role, *args, input=None):
        command = selection.command(role)
        require(command and os.path.isabs(command[0]), f'Explicit {role} command is required.')
        return runner([*command, *map(str, args)], input=input)

    try:
        expected = invoke('git', '-C', root, 'ls-files', '--stage', '--', 'upstream/pkgsrc')
    except Exception as error:
        if not hasattr(error, 'returncode'):
            raise
        expected = b''
    pins = [line.split()[1] for line in expected.splitlines() if line.startswith(b'160000 ')]
    try:
        actual = invoke('git', '-C', root / 'upstream/pkgsrc', 'rev-parse', 'HEAD').strip()
    except Exception as error:
        if not hasattr(error, 'returncode'):
            raise
        actual = b''
    require(len(pins) == 1 and pins[0] == actual,
            'Initialize the pinned submodule with git submodule update --init upstream/pkgsrc.')
    revision = pins[0].decode('ascii')
    scratch.mkdir(mode=0o700)
    archive = Path(scratch) / 'pkgsrc.tar'
    invoke('git', '-C', root / 'upstream/pkgsrc', 'archive', '--format=tar',
           '--output=' + str(archive), revision)
    destination.mkdir()
    extract_archive(archive, destination)
    replaces_file = root / 'pkgsrc/replaces'
    replaces = ([line.strip(' \t') for line in replaces_file.read_bytes().decode('utf-8').split('\n')
                 if line and not line.startswith('#')] if replaces_file.is_file() else [])
    names = {name for name, source in recipes}
    for name in replaces:
        require(name in names and joined(destination, name + '/Makefile').is_file(),
                f'pkgsrc/replaces names {name}, but no EmberBSD recipe or no upstream recipe has it.')
    for name, source in recipes:
        require(not os.path.lexists(joined(destination, name)) or name in replaces,
                f'Upstream already has {name}; add it to pkgsrc/replaces or remove it.')
    new_categories = set()
    for category in categories:
        target = destination / category.name
        if not target.exists():
            shutil.copytree(category, target, copy_function=copy_file)
            new_categories.add(category.name)
        elif (category / 'Makefile').is_file():
            raise ExportError(f'Upstream already has {category.name}; review the overlay.')
        else:
            for path in category.iterdir():
                if path.name.startswith('.'):
                    continue
                require(path.is_dir(), f'Unexpected overlay file: pkgsrc/{category.name}/{path.name}')
    for name, source in recipes:
        if source.is_relative_to(root / 'pkgsrc') and name.split('/')[0] in new_categories:
            continue
        target = joined(destination, name)
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, copy_function=copy_file)
    for method, source, recipe, name in patches:
        if method == 'patch':
            try:
                invoke('patch', '-f', '-E', '-d', destination, '-p1', '-F', '0', input=source.read_bytes())
            except Exception as error:
                if not hasattr(error, 'returncode'):
                    raise
                raise ExportError('Infrastructure patch does not apply: ' + str(source.relative_to(root))) from error
        elif method == 'git-apply':
            invoke('git', '-C', destination, 'apply', '--check', source)
            invoke('git', '-C', destination, 'apply', source)
        else:
            directory = joined(destination, recipe) / 'patches'
            directory.mkdir(exist_ok=True)
            target = directory / name
            require(not target.exists(), f'Recipe patch collision: {recipe}/patches/{name}')
            copy_file(source, target)
            with joined(destination, recipe + '/distinfo').open('a') as output:
                output.write(f'SHA1 ({name}) = {patch_sha1(source)}\n')
    for source, name in files:
        target = joined(destination, name)
        require(not target.exists(), f'Exported file collision: {name}')
        copy_file(source, target)
    (destination / 'EMBERBSD-PKGSRC-REVISION').write_text(revision + '\n')
    return revision


def main(argv=None):
    """Refuse standalone execution until SDK owns the exact export stage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    parser.add_argument('--sdk-source')
    for name in ('descriptor', 'accepted-seed-receipt', 'bootstrap-plan'):
        parser.add_argument('--' + name)
        parser.add_argument('--' + name + '-sha256')
    args = parser.parse_args(argv)
    try:
        destination_path(args.destination)
        raise ExportError('The SDK source-export controller is not available. '
                          'Do not reuse a grep, metadata or relocation acceptance. '
                          'Use the callable only inside its exact SDK controller, '
                          'or run the documented source-data composition tests.')
    except ExportError as error:
        print('prepare-pkgsrc: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
