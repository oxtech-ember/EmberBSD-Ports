#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted migration of prepare-pkgsrc.sh.
"""Export the complete pinned pkgsrc tree through explicitly selected tools."""

import argparse
import fnmatch
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True


class ExportError(ValueError):
    """An input cannot produce the canonical export."""


def require(value, message):
    if not value:
        raise ExportError(message)


def joined(root, relative):
    """Join an untrusted POSIX-relative path without accepting traversal."""
    parts = relative_parts(relative, 'export path')
    return Path(root).joinpath(*parts)


def relative_parts(value, label):
    require(isinstance(value, str) and value and not value.startswith('/') and
            '\\' not in value and not any(ord(char) < 32 or ord(char) == 127 for char in value),
            f'{label} must be a safe relative path.')
    parts = value.split('/')
    require(all(part not in ('', '.', '..') for part in parts),
            f'{label} must not contain empty, dot, or parent components.')
    return parts


def package_path(value, label):
    parts = relative_parts(value, label)
    require(len(parts) == 2, f'{label} must be a pkgsrc category/package path.')
    return '/'.join(parts)


def source_path(root, relative, label):
    """Resolve one source selector and keep symlink targets inside Ports."""
    path = joined(root, relative)
    base = Path(root).resolve(strict=True)
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ExportError(f'{label} does not resolve inside the Ports source: {relative}') from error
    require(resolved.is_relative_to(base),
            f'{label} resolves outside the Ports source: {relative}')
    return path


def destination_parent(root, relative):
    """Check each existing parent without following an export-tree symlink."""
    parts = relative_parts(relative, 'export destination')
    base = Path(root).resolve(strict=True)
    current = base
    for part in parts[:-1]:
        current = current / part
        if not os.path.lexists(current):
            break
        info = current.lstat()
        require(stat.S_ISDIR(info.st_mode),
                f'export destination has a non-directory or symlink parent: {current}')
        require(current.resolve(strict=True).is_relative_to(base),
                f'export destination escapes its root: {relative}')
    return base.joinpath(*parts)


def ensure_destination_directory(root, relative):
    """Create an export directory one checked component at a time."""
    parts = relative_parts(relative, 'export destination')
    base = Path(root).resolve(strict=True)
    current = base
    for part in parts:
        current = current / part
        if os.path.lexists(current):
            info = current.lstat()
            require(stat.S_ISDIR(info.st_mode),
                    f'export destination has a non-directory or symlink parent: {current}')
        else:
            current.mkdir()
        require(current.resolve(strict=True).is_relative_to(base),
                f'export destination escapes its root: {relative}')
    return current


def check_tree_links(root, source, label):
    """Reject copied-source links that leave Ports or resolve to directories."""
    root = Path(root).resolve(strict=True)
    source = Path(source)
    try:
        resolved_source = source.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ExportError(f'Incomplete source tree: {label}') from error
    require(resolved_source.is_relative_to(root),
            f'Source tree leaves the repository: {label}')
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
            require(resolved.is_file(), f'Link is not a regular file: {path}')


def destination_path(value):
    value = os.fspath(value)
    require(value.startswith('/'), 'Destination must be absolute.')
    require(re.fullmatch(r'[a-zA-Z0-9_./-]+', value),
            'pkgsrc requires a path without whitespace or shell metacharacters.')
    path = Path(value)
    require(not os.path.lexists(path), 'Destination already exists.')
    # Later checks compare resolved export paths with this one. Resolve the
    # existing parent so a symlinked parent, such as /var -> /private/var
    # below the default Darwin TMPDIR, names the same tree.
    path = path.parent.resolve() / path.name
    require(re.fullmatch(r'[a-zA-Z0-9_./-]+', str(path)),
            'pkgsrc requires a path without whitespace or shell metacharacters.')
    return path


def patch_sha1(path):
    raw = path.read_bytes()
    chunks = raw.split(b'\n')
    filtered = b''.join(line + (b'\n' if index < len(chunks) - 1 else b'')
                        for index, line in enumerate(chunks) if b'$NetBSD' not in line)
    return hashlib.sha1(filtered).hexdigest()


def check_recipe(source, label, root):
    root = Path(root).resolve(strict=True)
    source = Path(source).resolve(strict=True)
    require(source.is_relative_to(root), f'Recipe source leaves the repository: {label}')
    check_tree_links(root, source, label)
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


def configuration(root, *, include_manifests=False):
    root = Path(root).resolve(strict=True)
    source_path(root, 'pkgsrc/export.conf', 'export configuration')
    config = root / 'pkgsrc/export.conf'
    require(config.is_file(), 'Missing pkgsrc/export.conf.')
    recipes, patches, files, manifests = [], [], [], []
    # POSIX read with tab IFS collapses adjacent tabs. It ignores an unfinished
    # final record. Preserve this input grammar during the migration.
    for raw in config.read_bytes().decode('utf-8').split('\n')[:-1]:
        fields = re.split(r'\t+', raw.strip('\t'))
        method = fields[0]
        if not method or method.startswith('#'):
            continue
        require(len(fields) <= 4, f'pkgsrc/export.conf: too many fields for {method}.')
        first, second, third = (fields[1:] + ['', '', ''])[:3]
        source = source_path(root, first, 'export source')
        if method == 'recipe':
            require(second and not third, 'pkgsrc/export.conf: use recipe SOURCE PKGPATH.')
            second = package_path(second, 'PKGPATH')
            check_recipe(source, first, root)
            recipes.append((second, source))
        elif method == 'patch':
            require(not second, 'pkgsrc/export.conf: use patch FILE.')
            require(source.is_file() and source.stat().st_size, f'Missing infrastructure patch: {first}')
            patches.append((method, source, '', ''))
        elif method == 'git-apply':
            require(second and not third, 'pkgsrc/export.conf: use git-apply FILE MANIFEST.')
            second = source_path(root, second, 'patch manifest')
            manifests.append(second)
            require(source.is_file() and source.stat().st_size, f'Missing infrastructure patch: {first}')
            recorded = [line.split('\t')[1] for line in second.read_bytes().decode('utf-8').split('\n')
                        if line.split('\t')[0] == source.name and len(line.split('\t')) > 1]
            require(recorded == [hashlib.sha256(source.read_bytes()).hexdigest()],
                    f'Infrastructure patch differs from {second}: {first}')
            patches.append((method, source, '', ''))
        elif method == 'recipe-patch':
            require(third, 'pkgsrc/export.conf: use recipe-patch FILE PKGPATH NAME.')
            second = package_path(second, 'PKGPATH')
            third = relative_parts(third, 'recipe patch name')
            require(len(third) == 1, 'recipe patch name must be one path component.')
            third = third[0]
            require(source.is_file() and source.stat().st_size, f'Missing recipe patch: {first}')
            require(third.startswith('patch-'), f'Recipe patch names start with patch-: {third}')
            patches.append((method, source, second, third))
        elif method == 'file':
            require(second and not third, 'pkgsrc/export.conf: use file SOURCE DESTINATION.')
            second = '/'.join(relative_parts(second, 'file destination'))
            require(source.is_file(), f'Missing exported file: {first}')
            files.append((source, second))
        else:
            raise ExportError(f'pkgsrc/export.conf: unknown method {method}.')
    source_path(root, 'pkgsrc', 'pkgsrc source directory')
    categories = []
    for path in (root / 'pkgsrc').iterdir():
        if path.name.startswith('.'):
            continue
        info = path.lstat()
        require(not stat.S_ISLNK(info.st_mode),
                f'pkgsrc category must not be a symlink: {path.name}')
        if stat.S_ISDIR(info.st_mode):
            categories.append(path)
    categories.sort()
    for category in categories:
        check_tree_links(root, category, 'pkgsrc/' + category.name)
        for package in sorted(path for path in category.iterdir()
                              if path.is_dir() and not path.name.startswith('.')):
            name = category.name + '/' + package.name
            check_recipe(package, 'pkgsrc/' + name, root)
            recipes.append((name, package))
    names = [name for name, source in recipes]
    duplicate = next((name for name in sorted(names) if names.count(name) > 1), None)
    require(duplicate is None, f'Two recipe sources provide {duplicate}.')
    rules = version_families(root)
    old_version = next((name for name in names if version_pruned(name, rules)), None)
    require(old_version is None,
            f'Ports recipe {old_version} is an old version or needs one; pkgsrc/versions.mk removes it.')
    result = (recipes, patches, files, categories)
    return (*result, manifests) if include_manifests else result


VERSION_RULE = re.compile(r'EMBERBSD_VERSION_FAMILIES\+=[ \t]+([^ \t=]+)=([^ \t=]+)')
DEPENDENT_RULE = re.compile(r'EMBERBSD_VERSION_DEPENDENTS\+=[ \t]+([a-z0-9-]+/[^ \t=*?\[/]+)')


def version_families(root):
    """Return the FAMILY=KEPT rules of pkgsrc/versions.mk.

    A removed dependent PKGPATH is a rule whose KEPT is None.
    """
    path = Path(root) / 'pkgsrc/versions.mk'
    if not os.path.lexists(path):
        return []
    source_path(root, 'pkgsrc/versions.mk', 'version families')
    rules = []
    for line in path.read_bytes().decode('utf-8').split('\n'):
        if line.startswith('EMBERBSD_VERSION_DEPENDENTS'):
            match = DEPENDENT_RULE.fullmatch(line.rstrip(' \t'))
            require(match, 'pkgsrc/versions.mk: use EMBERBSD_VERSION_DEPENDENTS+= PKGPATH: ' + line)
            rules.append((match.group(1), None))
            continue
        if not line.startswith('EMBERBSD_VERSION_FAMILIES'):
            continue
        match = VERSION_RULE.fullmatch(line.rstrip(' \t'))
        require(match, 'pkgsrc/versions.mk: use EMBERBSD_VERSION_FAMILIES+= FAMILY=KEPT: ' + line)
        rules.append(match.groups())
    return rules


def version_pruned(name, rules):
    """Return the family that rejects PKGPATH name, or None."""
    for family, kept in rules:
        if fnmatch.fnmatchcase(name, family) and (
                kept is None or not fnmatch.fnmatchcase(name, kept)):
            return family
    return None


def prune_versions(destination, rules):
    """Remove old versions of each family from the export; keep exactly the KEPT paths."""
    destination = Path(destination)
    packages = sorted(category.name + '/' + package.name
                      for category in destination.iterdir()
                      if category.is_dir() and not category.is_symlink()
                      for package in category.iterdir()
                      if package.is_dir() and not package.is_symlink())
    for family, kept in rules:
        if kept is None:
            require(family in packages,
                    f'pkgsrc/versions.mk removes {family}, but the export has no such package.')
            continue
        require(any(fnmatch.fnmatchcase(name, kept) for name in packages),
                f'pkgsrc/versions.mk keeps {kept}, but the export has no such package.')
    removed = [name for name in packages if version_pruned(name, rules)]
    for name in removed:
        shutil.rmtree(destination_parent(destination, name))
    for category in sorted({name.split('/')[0] for name in removed}):
        makefile = destination_parent(destination, category + '/Makefile')
        if not makefile.is_file():
            continue
        gone = {name.split('/')[1] for name in removed if name.split('/')[0] == category}
        lines = makefile.read_bytes().decode('utf-8').split('\n')
        kept_lines = [line for line in lines
                      if not (line.startswith('SUBDIR') and line.split()[-1:] and
                              line.split()[-1] in gone)]
        makefile.write_bytes('\n'.join(kept_lines).encode('utf-8'))
    return removed


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


def patch_safety_options(selection, runner):
    """Select an optional patch behavior from its advertised capabilities."""
    command = selection.command('patch')
    require(command and os.path.isabs(command[0]), 'Explicit patch command is required.')
    try:
        help_text = runner([*command, '--help'])
    except Exception as error:
        if not hasattr(error, 'returncode'):
            raise
        return ()
    return (('--no-backup-if-mismatch',)
            if b'--no-backup-if-mismatch' in help_text else ())


def numbered_backup_paths(root, directories=None):
    """Return existing GNU-style numbered backup paths relative to a tree.

    With directories, only those directories (relative to root) are listed.
    """
    def backup(path):
        return path.is_file() and re.search(r'\.~[0-9]+~$', path.name)
    if directories is None:
        return {path.relative_to(root) for path in Path(root).rglob('*') if backup(path)}
    result = set()
    for directory in directories:
        path = Path(root, directory)
        if path.is_dir() and not path.is_symlink():
            result.update(item.relative_to(root) for item in path.iterdir() if backup(item))
    return result


def patched_directories(patches):
    """Return the directories in which patch -p1 may leave backup files.

    patch writes a backup next to each file it changes, and every such file
    is named on a ---/+++ header line.  Other lines may look like headers too;
    they only add directories.  None means the names are unknown, and the
    caller then scans the whole tree.
    """
    directories = set()
    for method, source, _, _ in patches:
        if method != 'patch':
            continue
        names = [line[4:].split(b'\t')[0].strip() for line in source.read_bytes().split(b'\n')
                 if line.startswith((b'--- ', b'+++ '))]
        names = [name for name in names if name != b'/dev/null']
        if not names:
            return None
        for name in names:
            parts = name.decode('utf-8', 'surrogateescape').split('/')[1:]
            if not parts or any(part in ('', '.', '..') for part in parts):
                return None
            directories.add('/'.join(parts[:-1]))
    return directories


def export_pkgsrc(root, destination, *, selection, runner, scratch):
    """Export once and return the upstream revision.

    selection supplies explicit command(role) tuples. runner(argv, cwd=None,
    input=None) returns captured bytes or raises the real child status.
    scratch is a new absolute caller-owned work child. This function never
    removes it. The caller cleans it after child completion and retains it on
    SDK ProcessOwnershipError. This function never searches the host PATH.
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

    patch_safety = patch_safety_options(selection, runner)

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
            'Initialize the pinned submodule with git submodule update --init --depth 1 upstream/pkgsrc.')
    revision = pins[0].decode('ascii')
    scratch.mkdir(mode=0o700)
    archive = Path(scratch) / 'pkgsrc.tar'
    invoke('git', '-C', root / 'upstream/pkgsrc', 'archive', '--format=tar',
           '--output=' + str(archive), revision)
    destination.mkdir()
    extract_archive(archive, destination)
    replaces_file = root / 'pkgsrc/replaces'
    if os.path.lexists(replaces_file):
        source_path(root, 'pkgsrc/replaces', 'pkgsrc replacements list')
    replaces = ([package_path(line.strip(' \t'), 'pkgsrc/replaces entry')
                 for line in replaces_file.read_bytes().decode('utf-8').split('\n')
                 if line.strip(' \t') and not line.startswith('#')] if replaces_file.is_file() else [])
    names = {name for name, source in recipes}
    for name in replaces:
        upstream_makefile = destination_parent(destination, name + '/Makefile')
        require(name in names and upstream_makefile.is_file(),
                f'pkgsrc/replaces names {name}, but no EmberBSD recipe or no upstream recipe has it.')
    for name, source in recipes:
        upstream_recipe = destination_parent(destination, name)
        require(not os.path.lexists(upstream_recipe) or name in replaces,
                f'Upstream already has {name}; add it to pkgsrc/replaces or remove it.')
    new_categories = set()
    for category in categories:
        target = destination_parent(destination, category.name)
        if not os.path.lexists(target):
            shutil.copytree(category, target, copy_function=copy_file)
            new_categories.add(category.name)
        else:
            require(stat.S_ISDIR(target.lstat().st_mode),
                    f'Export category is not a real directory: {category.name}')
            if (category / 'Makefile').is_file():
                raise ExportError(f'Upstream already has {category.name}; review the overlay.')
            else:
                for path in category.iterdir():
                    if path.name.startswith('.'):
                        continue
                    require(path.is_dir(), f'Unexpected overlay file: pkgsrc/{category.name}/{path.name}')
    for name, source in recipes:
        if source.is_relative_to(root / 'pkgsrc') and name.split('/')[0] in new_categories:
            continue
        target = destination_parent(destination, name)
        if os.path.lexists(target) and (target.is_symlink() or target.is_file()):
            target.unlink()
        elif os.path.lexists(target):
            require(stat.S_ISDIR(target.lstat().st_mode),
                    f'Unsupported existing export object: {name}')
            shutil.rmtree(target)
        ensure_destination_directory(destination, name.rpartition('/')[0])
        shutil.copytree(source, target, copy_function=copy_file)
    # Only directories of patched files can receive patch backups.
    backup_directories = patched_directories(patches)
    backup_baseline = numbered_backup_paths(destination, backup_directories)
    for method, source, recipe, name in patches:
        if method == 'patch':
            try:
                invoke('patch', '-f', '-E', '-d', destination, '-p1', '-F', '0', '-V', 'none',
                       *patch_safety, input=source.read_bytes())
            except Exception as error:
                if not hasattr(error, 'returncode'):
                    raise
                raise ExportError('Infrastructure patch does not apply: ' + str(source.relative_to(root))) from error
        elif method == 'git-apply':
            invoke('git', '-C', destination, 'apply', '--check', source)
            invoke('git', '-C', destination, 'apply', source)
        else:
            directory = ensure_destination_directory(destination, recipe + '/patches')
            target = directory / name
            require(not os.path.lexists(target), f'Recipe patch collision: {recipe}/patches/{name}')
            copy_file(source, target)
            distinfo = destination_parent(destination, recipe + '/distinfo')
            require(os.path.lexists(distinfo) and stat.S_ISREG(distinfo.lstat().st_mode),
                    f'Recipe distinfo is not a regular file: {recipe}/distinfo')
            fd = os.open(distinfo, os.O_WRONLY | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(fd, 'a', encoding='utf-8') as output:
                output.write(f'SHA1 ({name}) = {patch_sha1(source)}\n')
    new_backups = numbered_backup_paths(destination, backup_directories) - backup_baseline
    require(not new_backups, 'Patch application created numbered backup artifacts: ' +
            ', '.join(sorted(path.as_posix() for path in new_backups)))
    for source, name in files:
        target = destination_parent(destination, name)
        require(not os.path.lexists(target), f'Exported file collision: {name}')
        parent = target.parent.relative_to(destination).as_posix()
        if parent != '.':
            ensure_destination_directory(destination, parent)
        copy_file(source, target)
    prune_versions(destination, version_families(root))
    revision_file = destination_parent(destination, 'EMBERBSD-PKGSRC-REVISION')
    require(not os.path.lexists(revision_file), 'Exported revision file already exists.')
    with revision_file.open('x', encoding='ascii') as output:
        output.write(revision + '\n')
    return revision


def main(argv=None):
    """Export source data with explicit Git and patch commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    parser.add_argument('--sdk-source')
    parser.add_argument('--host-prefix')
    parser.add_argument('--git')
    parser.add_argument('--patch')
    args = parser.parse_args(argv)
    try:
        destination = destination_path(args.destination)
        root = Path(__file__).resolve().parents[1]
        if args.host_prefix:
            require(args.sdk_source and not args.git and not args.patch,
                    '--host-prefix requires --sdk-source instead of --git and --patch.')
            sys.path.insert(0, str(root / 'pkgsrc/lang/llvm/files'))
            from sdk_source import load_sdk
            load_sdk(['--sdk-source', args.sdk_source])
            from emberbsd_sdk.native_toolset import load_host_prefix
            selected = load_host_prefix(args.host_prefix, required_roles=('git', 'patch'))
        else:
            require(not args.sdk_source, '--sdk-source is used only with --host-prefix.')
            commands = {'git': args.git, 'patch': args.patch}
            for role, path in commands.items():
                require(path and os.path.isabs(path) and os.path.isfile(path)
                        and os.access(path, os.X_OK),
                        'Set --' + role + ' to an absolute executable path.')
            selected = SimpleNamespace(command=lambda role: (commands[role],),
                path=os.pathsep.join(dict.fromkeys(str(Path(path).parent)
                                                for path in commands.values())))
        env = dict(os.environ)
        env.update(PATH=selected.path, LC_ALL='C', GIT_OPTIONAL_LOCKS='0',
                   GIT_NO_LAZY_FETCH='1', PATCH_VERSION_CONTROL='none')

        def runner(command, *, cwd=None, input=None):
            return subprocess.run(command, cwd=cwd, input=input, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  check=True).stdout

        with tempfile.TemporaryDirectory(prefix='.pkgsrc-export-', dir=destination.parent) as temporary:
            revision = export_pkgsrc(root, destination, selection=selected,
                                     runner=runner, scratch=Path(temporary) / 'source')
        print('Exported pkgsrc ' + revision + ' to ' + str(destination))
        return 0
    except Exception as error:
        print('prepare-pkgsrc: ' + str(error), file=sys.stderr)
        status = getattr(error, 'returncode', 2)
        return status if status >= 0 else 128 - status


if __name__ == '__main__':
    sys.exit(main())
