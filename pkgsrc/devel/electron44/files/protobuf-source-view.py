#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compose an Electron GN source view using selected common sources."""
import os
import re
import ast
import hashlib
import errno
import stat
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def entries(source, omit):
    return {item.name: item for item in source.iterdir() if item.name not in omit}



def chromium_replacements(source):
    script = source / 'build/linux/unbundle/replace_gn_files.py'
    tree = ast.parse(script.read_text(), filename=str(script))
    assignments = [node for node in tree.body if isinstance(node, ast.Assign) and
                   any(isinstance(target, ast.Name) and target.id == 'REPLACEMENTS'
                       for target in node.targets)]
    require(len(assignments) == 1, 'invalid Chromium replacement inventory')
    mapping = ast.literal_eval(assignments[0].value)
    require(isinstance(mapping, dict), 'invalid Chromium replacement mapping')
    return mapping


def abseil_replacements(source):
    mapping = chromium_replacements(source)
    prefix = Path('third_party/abseil-cpp')
    result = {}
    for name, destination in mapping.items():
        if not name.startswith('absl_'):
            continue
        dest = Path(destination)
        require(not dest.is_absolute() and '..' not in dest.parts and dest.is_relative_to(prefix),
                'invalid Chromium Abseil mapping')
        shim = source / 'build/linux/unbundle' / (name + '.gn')
        require(shim.is_file(), 'missing Chromium Abseil shim: ' + name)
        rel = dest.relative_to(prefix)
        require(rel not in result and (source / dest).is_file(), 'invalid Abseil replacement target')
        result[rel] = shim
    require(result, 'Chromium Abseil replacements are missing')
    return result


def shim_masks(replacements):
    """Mask every literal shim header, including conditional literal additions."""
    masks = set()
    for destination, shim in replacements.items():
        text = re.sub(r'(?m)#.*$', '', shim.read_text())
        # The source view is shared by GN toolchains. Mask the union of literal
        # additions, such as the Windows minizip header, without evaluating GN.
        # Other conditional bodies and computed header expressions stay invalid.
        text = re.sub(r'\bif\s*\(\s*[A-Za-z_][A-Za-z0-9_]*\s*\)\s*\{\s*'
                      r'(headers\s*\+=\s*\[[^\]]*\])\s*\}', r'\1', text, flags=re.S)
        blocks = re.findall(r'\b(?:absl_)?shim_headers\("[^"\n]+"\)\s*\{([^{}]*)\}', text, re.S)
        require(len(blocks) == len(re.findall(r'\b(?:absl_)?shim_headers\s*\(', text)),
                'unsupported Chromium shim_headers block: ' + str(shim))
        for block in blocks:
            roots = re.findall(r'\broot_path\s*=\s*"([^"\n]+)"', block)
            headers = re.findall(r'\bheaders\s*(\+?=)\s*\[([^\]]*)\]', block, re.S)
            assignments = re.findall(r'\b(root_path|headers|prefix)\s*(?:\+=|=)', block)
            require(assignments.count('root_path') == len(roots) == 1 and
                    assignments.count('headers') == len(headers) and headers and
                    headers[0][0] == '=' and all(operator == '+=' for operator, _ in headers[1:]) and
                    assignments.count('prefix') <= 1,
                    'non-literal or multiple Chromium shim header assignments')
            if 'prefix' in assignments:
                require(re.search(r'\bprefix\s*=\s*"[^"\n]*"', block) is not None,
                        'non-literal Chromium shim prefix')
            remainder = re.sub(r'\broot_path\s*=\s*"[^"\n]+"', '', block)
            remainder = re.sub(r'\bheaders\s*(?:\+=|=)\s*\[[^\]]*\]', '', remainder, flags=re.S)
            remainder = re.sub(r'\bprefix\s*=\s*"[^"\n]*"', '', remainder)
            require(not remainder.strip(), 'unsupported Chromium shim expression: ' + str(shim))
            literals = ','.join(value for _, value in headers)
            names = re.findall(r'"([^"\n]+)"', literals)
            residue = re.sub(r'"[^"\n]+"|[,\s]', '', literals)
            require(names and not residue, 'unsupported Chromium shim header expression')
            prefixes = re.findall(r'\bprefix\s*=\s*"([^"\n]*)"', block)
            require(all('$' not in value and '\\' not in value
                        for value in roots + names + prefixes),
                    'interpolated or escaped Chromium shim string')
            base = destination.parent / roots[0]
            require(not base.is_absolute() and '..' not in base.parts,
                    'unsafe Chromium shim root')
            for name in names:
                path = Path(name)
                require(not path.is_absolute() and '..' not in path.parts and ';' not in name,
                        'unsafe Chromium shim header')
                masks.add(base / path)
    return masks


def abseil_masks(source, replacements):
    """Remove every bundled Abseil non-GN file from the selected view."""
    root = source / 'third_party/abseil-cpp'
    masks = shim_masks(replacements)
    for path in (root / 'absl').rglob('*'):
        require(not path.is_symlink(), 'Abseil source contains a symlink: ' + str(path))
        if path.is_file() and path.suffix not in ('.gn', '.gni'):
            masks.add(path.relative_to(root))
    return masks


def dependency_view(origin, dest, replacements, masks, *, verify=False, partial=False, current=Path()):
    require(verify or not partial, 'partial dependency view requires verification')
    expected = {p.name for p in origin.iterdir() if current / p.name not in masks}
    if verify:
        require(dest.is_dir() and not dest.is_symlink(), 'dependency view component must be local')
        present = {p.name for p in dest.iterdir()}
        require(present <= expected if partial else present == expected, 'dependency view entries changed')
    else:
        dest.mkdir()
    for item in origin.iterdir():
        rel = current / item.name
        if rel in masks:
            continue
        output = dest / item.name
        if partial and not os.path.lexists(output):
            continue
        descend = any(path != rel and rel in path.parents for path in set(replacements) | masks)
        if descend:
            require(item.is_dir() and not item.is_symlink(), 'invalid dependency view parent')
            dependency_view(item, output, replacements, masks, verify=verify, partial=partial, current=rel)
        else:
            target = replacements.get(rel, item)
            if verify:
                require(output.is_symlink() and os.readlink(output) == str(target),
                        'dependency view link changed: ' + str(output))
            else:
                output.symlink_to(target, target_is_directory=target.is_dir())


# Script interpreters resolve symlinks (Python sys.path[0], esbuild entry
# points), so generators under a linked directory report or import paths from
# the prepared workspace instead of the view.  These third_party trees are
# mirrored as local directories of hard links (copies across devices).  The
# Chromium root outside third_party is mirrored as a whole because its build
# scripts locate the source root from their own module paths.
MATERIALIZED_THIRD_PARTY = ('blink', 'dawn', 'devtools-frontend', 'node')


def _directory_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _scan_directory(directory, omit):
    """Enumerate one real directory and retain its identity for final check."""
    before = os.lstat(directory)
    require(stat.S_ISDIR(before.st_mode),
            'mirrored view component must be a real directory: ' + str(directory))
    with os.scandir(directory) as scan:
        entries = {item.name: item for item in scan if item.name not in omit}
    return entries, _directory_identity(before)


def _require_directory_unchanged(directory, identity):
    current = os.lstat(directory)
    require(stat.S_ISDIR(current.st_mode) and _directory_identity(current) == identity,
            'mirrored view directory changed during verification: ' + str(directory))


def _same_file_bytes(left, right):
    with open(left, 'rb') as a, open(right, 'rb') as b:
        while True:
            left_chunk = a.read(1024 * 1024)
            right_chunk = b.read(1024 * 1024)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def _created_subtree(root, created_files):
    """Measure a nonempty, entirely receipt-authorized regular-file tree."""
    root = Path(root)
    require(root.is_absolute(), 'created source directory must be absolute')
    rows = {}
    def visit(path, relative):
        info = os.lstat(path)
        identity = (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                    info.st_mtime_ns, info.st_ctime_ns)
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as scan:
                children = sorted(item.name for item in scan)
            require(children, 'created source directory is empty: ' + str(path))
            rows[relative] = (identity, None)
            for name in children:
                visit(path / name, relative / name)
        else:
            require(stat.S_ISREG(info.st_mode), 'created source subtree contains a non-regular file')
            expected = created_files.get(str(path))
            require(isinstance(expected, str) and re.fullmatch(r'[0-9a-f]{64}', expected),
                    'created source file is absent from receipt: ' + str(path))
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as handle:
                opened = os.fstat(handle.fileno())
                require((opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size,
                         opened.st_mtime_ns, opened.st_ctime_ns) == identity,
                        'created source file changed before reading')
                digest = hashlib.file_digest(handle, 'sha256').hexdigest()
            require(digest == expected, 'created source file differs from receipt: ' + str(path))
            rows[relative] = (identity, digest)
        after = os.lstat(path)
        require((after.st_dev, after.st_ino, after.st_mode, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns) == identity,
                'created source subtree changed during verification: ' + str(path))
    visit(root, Path())
    return rows


def _open_real_directory(path):
    """Open each directory without following symbolic links."""
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'invalid mirror directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:]:
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _reuse_firstparty(origin, old, output):
    """Reuse a verified old regular file only after a stable full comparison."""
    descriptors = []
    created = False
    created_inode = None
    try:
        try:
            old_dir = _open_real_directory(old.parent)
        except FileNotFoundError:
            return False
        descriptors.append(old_dir)
        new_dir = _open_real_directory(origin.parent)
        descriptors.append(new_dir)
        output_dir = _open_real_directory(output.parent)
        descriptors.append(output_dir)
        try:
            old_info = os.stat(old.name, dir_fd=old_dir, follow_symlinks=False)
            if not stat.S_ISREG(old_info.st_mode):
                return False
            old_fd = os.open(old.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=old_dir)
        except FileNotFoundError:
            return False
        descriptors.append(old_fd)
        new_fd = os.open(origin.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=new_dir)
        descriptors.append(new_fd)
        before_old, before_new = os.fstat(old_fd), os.fstat(new_fd)
        def identity(info):
            return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        require(identity(before_old) == identity(old_info), 'first-party old file changed before open')
        if (before_old.st_dev, before_old.st_ino) == (before_new.st_dev, before_new.st_ino):
            return False
        if not (stat.S_ISREG(before_old.st_mode) and stat.S_ISREG(before_new.st_mode)):
            return False
        if (stat.S_IMODE(before_old.st_mode), before_old.st_size) != (stat.S_IMODE(before_new.st_mode), before_new.st_size):
            return False
        while True:
            a, b = os.read(old_fd, 1024 * 1024), os.read(new_fd, 1024 * 1024)
            if a != b:
                return False
            if not a:
                break
        require(identity(os.fstat(old_fd)) == identity(before_old) and
                identity(os.fstat(new_fd)) == identity(before_new) and
                identity(os.stat(old.name, dir_fd=old_dir, follow_symlinks=False)) == identity(before_old) and
                identity(os.stat(origin.name, dir_fd=new_dir, follow_symlinks=False)) == identity(before_new),
                'first-party mirror input changed during comparison')
        try:
            created_inode = (before_old.st_dev, before_old.st_ino)
            os.link(old.name, output.name, src_dir_fd=old_dir, dst_dir_fd=output_dir, follow_symlinks=False)
            created = True
            result = os.stat(output.name, dir_fd=output_dir, follow_symlinks=False)
            old_after = os.fstat(old_fd)
            require((old_after.st_dev, old_after.st_ino, old_after.st_mode, old_after.st_size, old_after.st_mtime_ns) ==
                    (before_old.st_dev, before_old.st_ino, before_old.st_mode, before_old.st_size, before_old.st_mtime_ns) and
                    (result.st_dev, result.st_ino, result.st_mode, result.st_size, result.st_mtime_ns) ==
                    (before_old.st_dev, before_old.st_ino, before_old.st_mode, before_old.st_size, before_old.st_mtime_ns) and
                    identity(os.fstat(new_fd)) == identity(before_new) and
                    identity(os.stat(origin.name, dir_fd=new_dir, follow_symlinks=False)) == identity(before_new),
                    'first-party hardlink or new input changed')
        except OSError as error:
            if created or error.errno != errno.EXDEV:
                raise
            fd = os.open(output.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         stat.S_IMODE(before_old.st_mode), dir_fd=output_dir)
            created = True
            created_info = os.fstat(fd)
            created_inode = (created_info.st_dev, created_info.st_ino)
            descriptors.append(fd)
            os.lseek(old_fd, 0, os.SEEK_SET)
            while True:
                chunk = os.read(old_fd, 1024 * 1024)
                if not chunk:
                    break
                data = memoryview(chunk)
                while data:
                    count = os.write(fd, data)
                    require(count > 0, 'short write to first-party copy')
                    data = data[count:]
            os.fchmod(fd, stat.S_IMODE(before_old.st_mode))
            os.utime(fd, ns=(before_old.st_atime_ns, before_old.st_mtime_ns))
            result = os.fstat(fd)
            require((result.st_mode, result.st_size, result.st_mtime_ns) ==
                    (before_old.st_mode, before_old.st_size, before_old.st_mtime_ns),
                    'first-party copy metadata changed')
            require(identity(os.fstat(old_fd)) == identity(before_old), 'first-party source changed during copy')
            copied = os.open(output.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=output_dir)
            descriptors.append(copied)
            require(identity(os.fstat(copied)) == identity(result) and
                    identity(os.stat(output.name, dir_fd=output_dir, follow_symlinks=False)) == identity(result),
                    'first-party copied file changed before verification')
            os.lseek(old_fd, 0, os.SEEK_SET)
            while True:
                a, b = os.read(old_fd, 1024 * 1024), os.read(copied, 1024 * 1024)
                require(a == b, 'first-party copy content changed')
                if not a:
                    break
            require(identity(os.fstat(copied)) == identity(result) and
                    identity(os.fstat(fd)) == identity(result) and
                    identity(os.stat(output.name, dir_fd=output_dir, follow_symlinks=False)) == identity(result) and
                    identity(os.fstat(old_fd)) == identity(before_old) and
                    identity(os.fstat(new_fd)) == identity(before_new) and
                    identity(os.stat(origin.name, dir_fd=new_dir, follow_symlinks=False)) == identity(before_new),
                    'first-party source changed after copy')
        return True
    except BaseException:
        if created and created_inode is not None:
            try:
                current = os.stat(output.name, dir_fd=output_dir, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == created_inode:
                    os.unlink(output.name, dir_fd=output_dir)
            except FileNotFoundError:
                pass
        raise
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def mirror(origin, dest, *, verify=False, omit=frozenset(), generated_files=frozenset(), updates=None, nested_omit=frozenset(), created_files=None, created_links=None, retired=False, previous=None, firstparty_root=False):
    """Mirror source entries; verification may allow named regular GN outputs.

    Electron's GN build_electron_definitions action creates electron-api.json
    and electron.d.ts in the local electron source view. They are build
    products, not entries in the prepared source tree.
    """
    require(not retired or (verify and updates is None), 'retired mirror must be read-only')
    origin = Path(origin)
    dest = Path(dest)
    nested_omit = {Path(path) for path in nested_omit}
    excluded = set(omit) | {p.name for p in nested_omit if len(p.parts) == 1}
    generated = set(generated_files)
    require(all(isinstance(name, str) and name not in ('.', '..') and
                Path(name).name == name and
                '/' not in name and '\\' not in name for name in generated),
            'generated mirror entries must be simple file names')
    source_entries, source_identity = _scan_directory(origin, excluded)
    names = set(source_entries)
    if verify:
        local_entries, local_identity = _scan_directory(dest, excluded)
        # Interpreter byte-code caches written into the local mirror are build
        # products of the view, not source entries.
        cache = local_entries.get('__pycache__')
        if cache is not None and cache.name not in names:
            cache_info = cache.stat(follow_symlinks=False)
            if stat.S_ISDIR(cache_info.st_mode):
                local_entries.pop('__pycache__')
        for name in set(local_entries) - names:
            if name in generated:
                info = local_entries[name].stat(follow_symlinks=False)
                require(stat.S_ISREG(info.st_mode),
                        'generated mirrored view entry must be a regular file: ' + str(dest / name))
                local_entries.pop(name)
            elif updates is None:
                raise ValueError('unexpected generated mirrored view entry: ' + str(dest / name))
        if updates is not None:
            if set(local_entries) - names:
                raise _LayoutChanged('mirrored view entries changed: ' + str(dest))
            for name in names - set(local_entries):
                item = source_entries[name]
                info = item.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode) and created_files is not None:
                    require(not any(path.parts[0] == name for path in nested_omit),
                            'created subtree overlaps an omitted view component')
                    snapshot = _created_subtree(item.path, created_files)
                    updates.append((dest / name, 'directory', item.path, item.path, snapshot, None))
                    continue
                if stat.S_ISLNK(info.st_mode):
                    target = os.readlink(item.path)
                    if not created_links or created_links.get(str(item.path)) != target:
                        raise _LayoutChanged('mirrored view entries changed: ' + str(dest))
                    source_id = (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                                 info.st_mtime_ns, info.st_ctime_ns)
                    updates.append((dest / name, 'link', target, item.path, source_id, None))
                    continue
                if not stat.S_ISREG(info.st_mode):
                    raise _LayoutChanged('mirrored view entries changed: ' + str(dest))
                source_id = (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                             info.st_mtime_ns, info.st_ctime_ns)
                updates.append((dest / name, 'file', item.path, item.path, source_id, None))
        require(set(local_entries) == names or ((updates is not None or retired) and set(local_entries) <= names),
                'mirrored view entries changed: ' + str(dest))
    else:
        dest.mkdir()

    for name, item in source_entries.items():
        output = dest / name
        source_info = item.stat(follow_symlinks=False)
        if verify and name not in local_entries:
            continue
        if stat.S_ISLNK(source_info.st_mode):
            source_link = os.readlink(item.path)
            if verify:
                output_entry = local_entries[name]
                output_info = output_entry.stat(follow_symlinks=False)
                same = (stat.S_ISLNK(output_info.st_mode) and
                        os.readlink(output_entry.path) == source_link)
                if not same and updates is not None:
                    _add_update(updates, output, 'link', source_link, item.path, source_info)
                else:
                    require(same, 'mirrored view link changed: ' + str(output))
            else:
                output.symlink_to(source_link)
        elif stat.S_ISDIR(source_info.st_mode):
            if verify:
                output_info = local_entries[name].stat(follow_symlinks=False)
                require(stat.S_ISDIR(output_info.st_mode),
                        'mirrored view directory changed: ' + str(output))
            nested = {Path(*p.parts[1:]) for p in nested_omit if len(p.parts) > 1 and p.parts[0] == name}
            old_child = (Path(previous) / name if previous is not None and name != '.git' and
                         not (firstparty_root and name in {'third_party', 'electron', 'v8', 'out'}) else None)
            if old_child is not None and (not old_child.is_dir() or old_child.is_symlink()):
                old_child = None
            mirror(item.path, output, verify=verify, updates=updates, nested_omit=nested,
                   created_files=created_files, created_links=created_links, retired=retired, previous=old_child)
        else:
            require(stat.S_ISREG(source_info.st_mode),
                    'unsupported mirrored view file type: ' + str(item.path))
            if not verify:
                old_leaf = Path(previous) / name if previous is not None and name != '.git' else None
                if (old_leaf is not None and str(item.path) not in (created_files or {}) and
                        _reuse_firstparty(Path(item.path), old_leaf, output)):
                    continue
                try:
                    os.link(item.path, output)
                except OSError:
                    import shutil
                    shutil.copy2(item.path, output)
                continue
            output_entry = local_entries[name]
            output_info = output_entry.stat(follow_symlinks=False)
            same_inode = ((source_info.st_ino, source_info.st_dev) ==
                          (output_info.st_ino, output_info.st_dev))
            same = (stat.S_ISREG(output_info.st_mode) and
                    stat.S_IMODE(source_info.st_mode) == stat.S_IMODE(output_info.st_mode) and
                    (same_inode or
                     (source_info.st_size == output_info.st_size and
                      _same_file_bytes(item.path, output_entry.path))))
            if not same and updates is not None:
                _add_update(updates, output, 'file', item.path, item.path, source_info)
            else:
                require(same, 'mirrored view file changed: ' + str(output))

    _require_directory_unchanged(origin, source_identity)
    if verify:
        _require_directory_unchanged(dest, local_identity)


def mirrored(third_party):
    return {name for name in MATERIALIZED_THIRD_PARTY if (third_party / name).is_dir()}


def icu_replacements(source):
    require(chromium_replacements(source).get('icu') == 'third_party/icu/BUILD.gn',
            'invalid Chromium ICU replacement mapping')
    shim = source / 'build/linux/unbundle/icu.gn'
    require(shim.is_file(), 'missing Chromium ICU shim')
    return {Path('BUILD.gn'): shim}


def re2_replacements(source):
    require(chromium_replacements(source).get('re2') == 'third_party/re2/BUILD.gn',
            'invalid Chromium RE2 replacement mapping')
    shim = source / 'build/linux/unbundle/re2.gn'
    require(shim.is_file(), 'missing Chromium RE2 shim')
    return {Path('BUILD.gn'): shim}


# Electron's GN npm actions resolve these modules from electron/node_modules;
# expose only this build set from the common Ports module prefix so CI-only
# devDependencies stay out of the build and typeRoots sees only @types/node.
ELECTRON_BUILD_MODULES = ('@electron/asar', '@electron/docs-parser',
                          '@electron/typescript-definitions', '@types/node',
                          'pre-flight', 'rolldown', 'semver', 'typescript')


def electron_module_links(modules):
    import json
    expected, bins = {}, {}
    for name in ELECTRON_BUILD_MODULES:
        target = modules / name
        manifest = target / 'package.json'
        require(manifest.is_file() and not target.is_symlink(), 'missing common JS module: ' + name)
        data = json.loads(manifest.read_text())
        require(data.get('name') == name, 'common JS module name differs: ' + name)
        expected[name] = str(target)
        declared = data.get('bin') or {}
        if isinstance(declared, str):
            declared = {name.rsplit('/', 1)[-1]: declared}
        for command, relative in declared.items():
            require('/' not in command and command not in bins, 'invalid module command: ' + command)
            path = (target / relative).resolve(strict=True)
            require(path.is_relative_to(target), 'module command escapes its module: ' + command)
            bins[command] = str(path)
    links = {**expected, **{'.bin/' + c: t for c, t in bins.items()}}
    return links


def electron_module_view(modules, dest, *, verify=False):
    links = electron_module_links(modules)
    dirs = {str(Path(n).parent) for n in links if '/' in n}
    if not verify:
        dest.mkdir()
        for d in sorted(dirs):
            (dest / d).mkdir(parents=True, exist_ok=True)
        for name, target in links.items():
            (dest / name).symlink_to(target, target_is_directory=not name.startswith('.bin/'))
        return
    require(dest.is_dir() and not dest.is_symlink(), 'electron/node_modules must be a local view')
    found = {}
    for root, subdirs, files in os.walk(dest):
        for item in subdirs + files:
            path = Path(root) / item
            rel = str(path.relative_to(dest))
            if path.is_symlink():
                found[rel] = os.readlink(path)
                if item in subdirs:
                    subdirs.remove(item)
            else:
                require(path.is_dir() and rel in dirs, 'unexpected electron/node_modules entry: ' + rel)
    require(found == links, 'electron/node_modules view changed')


def python_edition_defaults(protobuf, protoc):
    """Render python_edition_defaults.py from the common source, as Bazel does."""
    import subprocess, tempfile
    template = protobuf / 'python/google/protobuf/internal/python_edition_defaults.py.template'
    text = template.read_text()
    require(text.count('DEFAULTS_VALUE') == 1, 'unexpected python edition defaults template')
    with tempfile.TemporaryDirectory(prefix='protobuf-edition-defaults-') as work:
        output = Path(work) / 'defaults.bin'
        subprocess.run([str(protoc), '-I' + str(protobuf / 'src'), '--edition_defaults_out=' + str(output),
                        '--edition_defaults_minimum=PROTO2', '--edition_defaults_maximum=2026',
                        str(protobuf / 'src/google/protobuf/descriptor.proto')], check=True)
        data = output.read_bytes()
    escaped = ''.join('\\%03o' % byte for byte in data)
    return text.replace('DEFAULTS_VALUE', escaped)


DESCRIPTOR_PB2 = 'descriptor_pb2.py'
PYTHON_PROTO_INPUTS = {
    DESCRIPTOR_PB2: 'google/protobuf/descriptor.proto',
    'compiler/plugin_pb2.py': 'google/protobuf/compiler/plugin.proto',
}


def python_protobuf_modules(protobuf, protoc):
    """Generate Chromium's required pyproto modules together with selected protoc."""
    import subprocess, tempfile
    source = protobuf / 'src'
    package = protobuf / 'python/google/protobuf'
    for relative in PYTHON_PROTO_INPUTS:
        require(not (package / relative).exists(),
                'common protobuf Python tree already ships generated module: ' + relative)
    with tempfile.TemporaryDirectory(prefix='protobuf-python-modules-') as work:
        subprocess.run([str(protoc), '-I' + str(source), '--python_out=' + work,
                        *(str(source / relative) for relative in PYTHON_PROTO_INPUTS.values())], check=True)
        return {relative: (Path(work) / 'google/protobuf' / relative).read_bytes()
                for relative in PYTHON_PROTO_INPUTS}


def mirror_generated_python(origin, dest, generated, *, verify=False):
    """Mirror one runtime subtree while writing or verifying generated leaves."""
    groups = {}
    files = {}
    for relative, data in generated.items():
        parts = Path(relative).parts
        if len(parts) == 1:
            files[parts[0]] = data
        else:
            groups.setdefault(parts[0], {})[Path(*parts[1:]).as_posix()] = data
    mirror(origin, dest, verify=verify, omit=set(groups) | set(files))
    for name, children in groups.items():
        mirror_generated_python(origin / name, dest / name, children, verify=verify)
    for name, data in files.items():
        output = dest / name
        if verify:
            require(output.is_file() and not output.is_symlink() and output.read_bytes() == data,
                    'generated Python module changed: ' + str(output))
        else:
            output.write_bytes(data)


def python_view(protobuf, dest, protoc, *, verify=False):
    """Mirror the common pyproto runtime and add Chromium's generated Python inputs."""
    generated = {
        'google/protobuf/' + relative: data
        for relative, data in python_protobuf_modules(protobuf, protoc).items()
    }
    generated['google/protobuf/internal/python_edition_defaults.py'] = (
        python_edition_defaults(protobuf, protoc).encode())
    mirror_generated_python(protobuf / 'python', dest, generated, verify=verify)


def create(source, protobuf, destination, *, node=None, perfetto=None, v8=None, system_abseil=False, system_icu=False, system_re2=False, node_modules=None, protobuf_protoc=None, previous_view=None, created_files=None):
    source = Path(source).resolve(strict=True)
    protobuf = Path(protobuf).resolve(strict=True) if protobuf is not None else None
    v8 = Path(v8).resolve(strict=True) if v8 is not None else None
    if v8:
        require((v8 / 'BUILD.gn').is_file() and (v8 / 'include/v8-version.h').is_file(),
                'incomplete common V8 source')
    destination = Path(destination)
    if previous_view is not None:
        previous_view = Path(previous_view)
        require(previous_view.is_absolute() and previous_view.is_dir() and not previous_view.is_symlink(),
                'previous source view must be an absolute real directory')
    require(destination.is_absolute() and not os.path.lexists(destination),
            'source view destination must be a new absolute path')
    destination = destination.resolve()
    providers = {name: Path(value).resolve(strict=True) for name, value in
                 (('electron_node', node), ('perfetto', perfetto)) if value is not None}
    for name, marker in (('electron_node', 'node.gni'), ('perfetto', 'gn/perfetto.gni')):
        if name in providers:
            require((providers[name] / marker).is_file(), 'incomplete common source: ' + name)
    for parent in (source, *([protobuf] if protobuf else []), *([v8] if v8 else []), *providers.values()):
        require(not destination.is_relative_to(parent) and not parent.is_relative_to(destination),
                'source view overlaps an input')
    third_party = source / 'third_party'
    original = third_party / 'protobuf'
    require((source / '.gn').is_file(), 'incomplete Electron source')
    if protobuf:
        require(original.is_dir() and (protobuf / 'src').is_dir() and
                (protobuf / 'third_party').is_dir(), 'incomplete common Protobuf source')
    if node_modules is not None:
        electron_module_links(Path(node_modules).resolve(strict=True))
    destination.mkdir(parents=True)
    def links(origin, dest, omit):
        dest.mkdir()
        for name, item in entries(origin, omit).items():
            (dest / name).symlink_to(item, target_is_directory=item.is_dir())
    mirror(source, destination / 'src', omit={'third_party', 'out'} | ({'v8'} if v8 else set()),
           previous=(Path(previous_view) / 'src') if previous_view is not None else None,
           created_files=created_files, firstparty_root=True)
    if v8:
        (destination / 'src/v8').symlink_to(v8, target_is_directory=True)
    (destination / 'src/out').mkdir()
    links(third_party, destination / 'src/third_party', ({'protobuf'} if protobuf else set()) | set(providers) | ({'abseil-cpp'} if system_abseil else set()) | ({'icu'} if system_icu else set()) | ({'re2'} if system_re2 else set()) | mirrored(third_party))
    for name in mirrored(third_party):
        nested = {Path('src/node_modules')} if name == 'devtools-frontend' and node_modules is not None else frozenset()
        mirror(third_party / name, destination / 'src/third_party' / name, nested_omit=nested)
        if nested:
            (destination / 'src/third_party' / name / 'src/node_modules').symlink_to(
                Path(node_modules).resolve(strict=True), target_is_directory=True)
    if node_modules is not None:
        # WebUI scripts import third_party/node/node_modules statically; bind
        # it to the selected common Ports module prefix.
        modules = Path(node_modules).resolve(strict=True)
        require((third_party / 'node').is_dir() and not (third_party / 'node/node_modules').exists(),
                'Chromium third_party/node must not carry node_modules')
        node_view = destination / 'src/third_party/node'
        require(node_view.is_dir() and not node_view.is_symlink(), 'third_party/node must be mirrored')
        (node_view / 'node_modules').symlink_to(modules, target_is_directory=True)
        electron = destination / 'src/electron'
        require(electron.is_dir() and not electron.is_symlink() and
                not os.path.lexists(source / 'electron/node_modules'),
                'Electron source must be mirrored without node_modules')
        electron_module_view(modules, electron / 'node_modules')
    if system_abseil:
        replacements = abseil_replacements(source)
        dependency_view(third_party / 'abseil-cpp', destination / 'src/third_party/abseil-cpp',
                        replacements, abseil_masks(source, replacements))
    if system_icu:
        replacements = icu_replacements(source)
        dependency_view(third_party / 'icu', destination / 'src/third_party/icu',
                        replacements, shim_masks(replacements))
    if system_re2:
        replacements = re2_replacements(source)
        dependency_view(third_party / 're2', destination / 'src/third_party/re2',
                        replacements, shim_masks(replacements))
    for name, path in providers.items():
        (destination / 'src/third_party' / name).symlink_to(path, target_is_directory=True)
    if protobuf:
        common = ('src', 'third_party') + (('python',) if protobuf_protoc else ())
        links(original, destination / 'src/third_party/protobuf', set(common))
        for name in ('src', 'third_party'):
            (destination / 'src/third_party/protobuf' / name).symlink_to(protobuf / name,
                                                                         target_is_directory=True)
        if protobuf_protoc:
            # The pyproto runtime must match the selected protoc gencode.
            python_view(protobuf, destination / 'src/third_party/protobuf/python', protobuf_protoc)
    return destination / 'src'


def verify(source, protobuf, destination, *, node=None, perfetto=None, v8=None, system_abseil=False, system_icu=False, system_re2=False, node_modules=None, protobuf_protoc=None, ml_names=(), ml_verify=None, _updates=None, _refresh=False, _initial_missing=None, _legacy_devtools=False, _migration=False, _created_files=None, _created_links=None, _retired=False):
    require(not _retired or (_updates is None and not _refresh and not _migration and _initial_missing is None),
            'retired view verification must be read-only')
    source = Path(source).resolve(strict=True)
    protobuf = Path(protobuf).resolve(strict=True) if protobuf is not None else None
    providers = {name: Path(value).resolve(strict=True) for name, value in
                 (('electron_node', node), ('perfetto', perfetto)) if value is not None}
    v8 = Path(v8).resolve(strict=True) if v8 is not None else None
    destination = Path(destination)
    require(_refresh or not os.path.lexists(_refresh_marker(destination)),
            'source view refresh is incomplete; rerun refresh')
    require(_migration or not os.path.lexists(destination.parent / ('.' + destination.name + '.devtools-modules-migration')),
            'DevTools modules migration is incomplete; rerun migration')
    require(_migration or not os.path.lexists(destination.parent / ('.' + destination.name + '.common-components-migration')),
            'common components migration is incomplete; rerun migration')
    require(_migration or not os.path.lexists(destination.parent / ('.' + destination.name + '.ml-components-migration')),
            'ML components migration is incomplete; rerun migration')
    require(_migration or not os.path.lexists(destination.parent / ('.' + destination.name + '.header-components-migration')),
            'header components migration is incomplete; rerun migration')
    require(_migration or not os.path.lexists(destination.parent / ('.' + destination.name + '.media-header-components-migration')),
            'incomplete media header component migration')
    require(_migration or not os.path.lexists(destination.parent / ('.' + destination.name + '.compression-components-migration')),
            'incomplete compression component migration')
    require(_migration or not os.path.lexists(destination.parent / ('.' + destination.name + '.boringssl-components-migration')),
            'incomplete BoringSSL source migration')
    require(bool(ml_names) == bool(ml_verify), 'ML view selection is incomplete')
    require(destination.is_dir() and not destination.is_symlink(), 'source view must be a local directory')
    destination = destination.resolve(strict=True)
    def check(origin, dest, omit, extra):
        require(dest.is_dir() and not dest.is_symlink(), 'source view component must be a local directory: ' + str(dest))
        expected = entries(origin, omit)
        actual = set(item.name for item in dest.iterdir())
        allowed = set(expected) | set(extra)
        require(actual <= allowed and set(expected) <= actual and
                (_initial_missing is not None or actual == allowed),
                'source view entries changed: ' + str(dest))
        for name, item in expected.items():
            link = dest / name
            require(link.is_symlink() and os.readlink(link) == str(item),
                    'source view link changed: ' + str(link))
    root = destination / 'src'
    root_special = {'third_party', 'out'} | ({'v8'} if v8 else set())
    mirror(source, root, verify=True, omit=root_special | ({'electron'} if node_modules is not None else set()), updates=_updates, created_files=_created_files, created_links=_created_links, retired=_retired)
    if node_modules is not None:
        mirror(source / 'electron', root / 'electron', verify=True, omit={'node_modules'},
               generated_files={'electron-api.json', 'electron.d.ts'}, updates=_updates, created_files=_created_files, created_links=_created_links, retired=_retired)
    require({item.name for item in root.iterdir()} >= root_special, 'source view root entries changed')
    if v8:
        _check_provider_link(root / 'v8', v8, _updates)
    require((root / 'out').is_dir() and not (root / 'out').is_symlink(),
            'source view out must be local')
    replaced = ({'protobuf'} if protobuf else set()) | set(providers) | ({'abseil-cpp'} if system_abseil else set()) | ({'icu'} if system_icu else set()) | ({'re2'} if system_re2 else set()) | mirrored(source / 'third_party') | set(ml_names)
    check(source / 'third_party', root / 'third_party', replaced, replaced)
    if ml_verify:
        ml_verify()
    for name in mirrored(source / 'third_party'):
        nested = {Path('src/node_modules')} if name == 'devtools-frontend' and node_modules is not None and not _legacy_devtools else frozenset()
        mirror(source / 'third_party' / name, root / 'third_party' / name, verify=True,
               omit={'node_modules'} if name == 'node' and node_modules is not None else frozenset(),
               updates=_updates, nested_omit=nested, created_files=_created_files, created_links=_created_links, retired=_retired)
        if nested:
            link = root / 'third_party' / name / 'src/node_modules'
            require(link.is_symlink() and os.readlink(link) == str(Path(node_modules).resolve(strict=True)),
                    'DevTools common node_modules link changed')
    if node_modules is not None:
        link = root / 'third_party/node/node_modules'
        require(link.is_symlink() and os.readlink(link) == str(Path(node_modules).resolve(strict=True)),
                'common node_modules link changed')
        module_view = root / 'electron/node_modules'
        if _initial_missing is not None and not os.path.lexists(module_view):
            _initial_missing.append(('modules', module_view, Path(node_modules).resolve(strict=True)))
        else:
            electron_module_view(Path(node_modules).resolve(strict=True), module_view, verify=True)
    if system_abseil:
        component = root / 'third_party/abseil-cpp'
        if _initial_missing is not None and not os.path.lexists(component):
            _initial_missing.append(('abseil', component, None))
        else:
            replacements = abseil_replacements(source)
            dependency_view(source / 'third_party/abseil-cpp', root / 'third_party/abseil-cpp',
                            replacements, abseil_masks(source, replacements), verify=True)
    if system_icu:
        component = root / 'third_party/icu'
        if _initial_missing is not None and not os.path.lexists(component):
            _initial_missing.append(('icu', component, None))
        else:
            replacements = icu_replacements(source)
            dependency_view(source / 'third_party/icu', root / 'third_party/icu',
                            replacements, shim_masks(replacements), verify=True)
    if system_re2:
        component = root / 'third_party/re2'
        if _initial_missing is not None and not os.path.lexists(component):
            _initial_missing.append(('re2', component, None))
        else:
            replacements = re2_replacements(source)
            dependency_view(source / 'third_party/re2', root / 'third_party/re2',
                            replacements, shim_masks(replacements), verify=True)
    for name, path in providers.items():
        link = root / 'third_party' / name
        if _initial_missing is not None and not os.path.lexists(link):
            _initial_missing.append(('link', link, path))
        else:
            _check_provider_link(link, path, _updates)
    if protobuf:
        path = root / 'third_party/protobuf'
        if _initial_missing is not None and not os.path.lexists(path):
            _initial_missing.append(('protobuf', path, Path(protobuf)))
        else:
            common = {'src', 'third_party'} | ({'python'} if protobuf_protoc else set())
            check(source / 'third_party/protobuf', path, common, common)
            if protobuf_protoc:
                python_view(protobuf, path / 'python', protobuf_protoc, verify=True)
            for name in ('src', 'third_party'):
                link = path / name
                require(link.is_symlink() and os.readlink(link) == str(protobuf / name),
                        'common Protobuf source link changed: ' + str(link))
    return root



def complete_initial(source, protobuf, destination, **sources):
    """Complete missing tail components of an interrupted initial create."""
    import tempfile
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve(strict=True)
    modules = sources.get('node_modules')
    if modules is not None:
        electron_module_links(Path(modules).resolve(strict=True))
    missing = []
    verify(source, protobuf, destination, **sources, _initial_missing=missing)
    third_party = source / 'third_party'
    for kind, target, value in missing:
        require(not os.path.lexists(target), 'initial component appeared: ' + str(target))
        if kind == 'link':
            target.symlink_to(value, target_is_directory=True)
            continue
        with tempfile.TemporaryDirectory(prefix='.source-component-', dir=target.parent) as temp:
            staged = Path(temp) / 'component'
            if kind == 'modules':
                electron_module_view(value, staged)
            elif kind == 'protobuf':
                staged.mkdir()
                common = {'src', 'third_party'} | ({'python'} if sources.get('protobuf_protoc') else set())
                for name, item in entries(third_party / 'protobuf', common).items():
                    (staged / name).symlink_to(item, target_is_directory=item.is_dir())
                for name in ('src', 'third_party'):
                    (staged / name).symlink_to(value / name, target_is_directory=True)
                if sources.get('protobuf_protoc'):
                    python_view(value, staged / 'python', sources['protobuf_protoc'])
            else:
                name = {'abseil': 'abseil-cpp', 'icu': 'icu', 're2': 're2'}[kind]
                replacements = {'abseil': abseil_replacements, 'icu': icu_replacements,
                                're2': re2_replacements}[kind](source)
                masks = abseil_masks(source, replacements) if kind == 'abseil' else shim_masks(replacements)
                dependency_view(third_party / name, staged, replacements, masks)
            require(not os.path.lexists(target), 'initial component appeared: ' + str(target))
            staged.rename(target)
    return destination / 'src'



class _LayoutChanged(ValueError):
    """The leaf-only refresh cannot represent this structural source change."""


def _refresh_marker(destination):
    destination = Path(destination)
    return destination.parent / ('.' + destination.name + '-refresh-incomplete')


def _leaf_identity(path, *, dir_fd=None):
    info = os.stat(path, dir_fd=dir_fd, follow_symlinks=False)
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _add_update(updates, output, kind, value, origin=None, info=None):
    previous = os.lstat(output)
    require(stat.S_ISREG(previous.st_mode) or stat.S_ISLNK(previous.st_mode),
            'incremental view leaf has an unsupported type: ' + str(output))
    source_identity = None
    if origin is not None:
        source_identity = (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                           info.st_mtime_ns, info.st_ctime_ns)
    updates.append((Path(output), kind, str(value), origin, source_identity,
                    _leaf_identity(output)))


def _check_provider_link(link, target, updates):
    require(link.is_symlink(), 'common source must remain a link: ' + str(link))
    if os.readlink(link) != str(target):
        if updates is None:
            raise ValueError('common source link changed: ' + str(link))
        _add_update(updates, link, 'link', target)


def _copy_leaf(source, destination, *, hardlink=False):
    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    else:
        if hardlink:
            try:
                os.link(source, destination)
                return
            except OSError:
                pass
        import shutil
        shutil.copy2(source, destination)


def _refresh_leaves(source, protobuf, destination, sources, *, created_files=None, created_links=None, publication=None):
    """Update only verified leaves under the caller's exclusive source lock.

    Ordinary failures restore the previous leaves. An interrupted process
    leaves a marker which refuses ordinary verification. A later refresh
    finishes forward from verified source inputs; it does not trust a saved
    file-operation journal. The controller also guards the GN configuration.
    """
    import tempfile
    from contextlib import ExitStack

    destination = destination.resolve(strict=True)
    marker = _refresh_marker(destination)
    recovering = os.path.lexists(marker)
    if recovering:
        require(stat.S_ISREG(os.lstat(marker).st_mode) and
                marker.read_text() == 'source-view-leaves-v1\n',
                'invalid source view refresh marker')
    updates = []
    extra = {'_created_files': created_files} if created_files is not None else {}
    if created_links is not None:
        extra['_created_links'] = created_links
    verify(source, protobuf, destination, **sources, _updates=updates, _refresh=True, **extra)
    if not updates:
        if recovering:
            marker.unlink()
        return destination / 'src'

    with tempfile.TemporaryDirectory(prefix='.source-view-leaves-',
                                     dir=destination.parent) as temporary, ExitStack() as handles:
        staged = Path(temporary)
        parents = {}
        parent_fds = {}
        old_states = {}
        work_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        handles.callback(os.close, work_fd)
        new_identities = []
        created_trees = {}
        for index, (output, kind, value, origin, expected_source, expected_old) in enumerate(updates):
            old_key = expected_old[:2] if expected_old is not None else None
            expected_old = old_states.get(old_key, expected_old)
            parent = output.parent
            while True:
                require(parent.is_relative_to(destination), 'view update escapes its root')
                info = os.lstat(parent)
                require(stat.S_ISDIR(info.st_mode), 'view update parent is not local')
                parents[parent] = (info.st_dev, info.st_ino)
                if parent == destination:
                    break
                parent = parent.parent
            if output.parent not in parent_fds:
                fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                handles.callback(os.close, fd)
                info = os.fstat(fd)
                require((info.st_dev, info.st_ino) == parents[output.parent],
                        'view update parent changed while opening')
                parent_fds[output.parent] = fd
            if expected_old is None:
                require(not os.path.lexists(output), 'new view leaf appeared before staging')
            else:
                require(_leaf_identity(output) == expected_old, 'view leaf changed before staging')
            if origin is not None and kind == 'directory':
                require(publication is not None and _created_subtree(origin, created_files) == expected_source,
                        'created source subtree changed before staging')
            elif origin is not None:
                require(_leaf_identity(origin) == expected_source and
                        (kind != 'link' or os.readlink(origin) == value),
                        'source leaf changed before staging')
            new = staged / ('new-' + str(index))
            if kind == 'link':
                new.symlink_to(value)
            elif kind == 'directory':
                import shutil
                shutil.copytree(value, new, symlinks=True, copy_function=shutil.copy2)
                require(_created_subtree(origin, created_files) == expected_source,
                        'created source subtree changed during staging')
                stage_map = {str(new / rel): digest for rel, (_, digest) in expected_source.items()
                             if digest is not None}
                stage_tree = _created_subtree(new, stage_map)
                require(set(stage_tree) == set(expected_source) and all(
                    (entry[0][2] & 0o7777, entry[0][4], entry[1]) ==
                    (expected_source[rel][0][2] & 0o7777, expected_source[rel][0][4],
                     expected_source[rel][1]) and
                    (entry[1] is None or entry[0][3] == expected_source[rel][0][3])
                    for rel, entry in stage_tree.items()),
                    'staged source subtree differs')
                created_trees[index] = (stage_map, stage_tree)
            else:
                _copy_leaf(Path(value), new)
            if origin is not None and kind != 'directory':
                require(_leaf_identity(origin) == expected_source and
                        (kind != 'link' or os.readlink(origin) == value),
                        'source leaf changed during staging')
            if expected_old is not None:
                _copy_leaf(output, staged / ('old-' + str(index)), hardlink=True)
                current_old = _leaf_identity(output)
                # A hardlink backup changes ctime and the link count, not payload.
                require(current_old[:5] == expected_old[:5], 'view leaf changed during staging')
                updates[index] = (output, kind, value, origin, expected_source, current_old)
                old_states[old_key] = current_old
            new_identities.append(_leaf_identity(new)[:5])

        if not recovering:
            fd = os.open(marker.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=work_fd)
            with os.fdopen(fd, 'w') as handle:
                handle.write('source-view-leaves-v1\n')
        installed = []
        try:
            for index, (output, kind, value, origin, expected_source, expected_old) in enumerate(updates):
                old_key = expected_old[:2] if expected_old is not None else None
                if old_key is not None:
                    expected_old = old_states[old_key]
                for parent, expected in parents.items():
                    info = os.lstat(parent)
                    require(stat.S_ISDIR(info.st_mode) and
                            (info.st_dev, info.st_ino) == expected,
                            'view update parent changed')
                if expected_old is None:
                    require(not os.path.lexists(output), 'new view leaf appeared before install')
                else:
                    require(_leaf_identity(output) == expected_old, 'view leaf changed before install')
                if origin is not None and kind == 'directory':
                    require(_created_subtree(origin, created_files) == expected_source,
                            'created source subtree changed before install')
                elif origin is not None:
                    require(_leaf_identity(origin) == expected_source and
                            (kind != 'link' or os.readlink(origin) == value),
                            'source leaf changed before install')
                fd = parent_fds[output.parent]
                if kind == 'directory':
                    _, tree = created_trees[index]
                    actual_map = {str(output / rel): digest for rel, (_, digest) in tree.items()
                                  if digest is not None}
                    created_trees[index] = (actual_map, tree)
                    publication.publish_directory_noreplace(staged / ('new-' + str(index)), output)
                    installed.append(index)
                    actual = _created_subtree(output, actual_map)
                    require(all(actual[rel][0][:5] == tree[rel][0][:5] and actual[rel][1] == tree[rel][1]
                                for rel in tree) and set(actual) == set(tree),
                            'installed source subtree changed')
                    created_trees[index] = (actual_map, actual)
                    require(_created_subtree(origin, created_files) == expected_source,
                            'created source subtree changed during install')
                elif expected_old is None:
                    os.link(staged / ('new-' + str(index)), output.name,
                            dst_dir_fd=fd, follow_symlinks=False)
                    installed.append(index)
                else:
                    installed.append(index)
                    os.replace(staged / ('new-' + str(index)), output.name, dst_dir_fd=fd)
                require(_leaf_identity(output.name, dir_fd=fd)[:5] == new_identities[index],
                        'installed source view leaf changed')
                if origin is not None and kind == 'link':
                    require(_leaf_identity(origin) == expected_source and os.readlink(origin) == value,
                            'source link changed during install')
                if expected_old is None:
                    continue
                # Installing one name can change ctime of other names for
                # the old inode. Retain the observed identity of that inode.
                backup_identity = _leaf_identity(staged / ('old-' + str(index)))
                if backup_identity[:2] == old_key:
                    old_states[old_key] = backup_identity
                else:
                    for remaining in updates[index + 1:]:
                        if remaining[5] is not None and remaining[5][:2] == old_key:
                            sibling = remaining[0]
                            observed = _leaf_identity(sibling.name, dir_fd=parent_fds[sibling.parent])
                            require(observed[:5] == remaining[5][:5],
                                    'view alias changed during install')
                            old_states[old_key] = observed
                            break
        except BaseException:
            for index in reversed(installed):
                output = updates[index][0]
                fd = parent_fds[output.parent]
                if updates[index][1] == 'directory':
                    import shutil
                    actual_map, tree = created_trees[index]
                    require(_created_subtree(output, actual_map) == tree,
                            'new view subtree changed before rollback')
                    shutil.rmtree(output)
                elif updates[index][5] is None:
                    require(_leaf_identity(output.name, dir_fd=fd)[:5] == new_identities[index],
                            'new view leaf changed before rollback')
                    os.unlink(output.name, dir_fd=fd)
                else:
                    os.replace(staged / ('old-' + str(index)), output.name, dst_dir_fd=fd)
            local = True
            for parent, expected in parents.items():
                try:
                    info = os.lstat(parent)
                    local = local and stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == expected
                except OSError:
                    local = False
            if not recovering and local:
                os.unlink(marker.name, dir_fd=work_fd)
            raise
        os.unlink(marker.name, dir_fd=work_fd)
    return destination / 'src'


def _write_transaction_marker(marker, content):
    """Atomically record a source-view transaction state."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', dir=marker.parent, prefix='.source-view-marker-', delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(content); f.flush(); os.fsync(f.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, marker)
    finally:
        temporary.unlink(missing_ok=True)


def migrate_devtools_modules(source, protobuf, destination, **sources):
    """Replace only the verified legacy DevTools modules mirror under the source lock."""
    import shutil
    destination = Path(destination).resolve(strict=True)
    modules = Path(sources['node_modules']).resolve(strict=True)
    origin = Path(source).resolve(strict=True) / 'third_party/devtools-frontend/src/node_modules'
    selected = destination / 'src/third_party/devtools-frontend/src/node_modules'
    backup = destination.parent / ('.' + destination.name + '.devtools-modules-old')
    pending = destination.parent / ('.' + destination.name + '.devtools-modules-next')
    marker = destination.parent / ('.' + destination.name + '.devtools-modules-migration')
    def mark_committed():
        _write_transaction_marker(marker, 'devtools-modules-committed-v1\n')

    if os.path.lexists(marker):
        require(marker.is_file() and not marker.is_symlink(), 'invalid DevTools migration marker')
        state = marker.read_text()
        require(state in ('devtools-modules-v1\n', 'devtools-modules-committed-v1\n'),
                'invalid DevTools migration marker')
        if state == 'devtools-modules-committed-v1\n':
            require(selected.is_symlink() and os.readlink(selected) == str(modules),
                    'invalid committed DevTools selection')
            verify(source, protobuf, destination, **sources, _migration=True)
            if os.path.lexists(backup):
                require(backup.is_dir() and not backup.is_symlink(), 'invalid DevTools migration backup')
                shutil.rmtree(backup)
        elif os.path.lexists(backup):
            require(backup.is_dir() and not backup.is_symlink(), 'invalid DevTools migration backup')
            mirror(origin, backup, verify=True)
            if not os.path.lexists(selected):
                backup.rename(selected)
            else:
                require(selected.is_symlink() and os.readlink(selected) == str(modules),
                        'invalid DevTools migration selection')
                verify(source, protobuf, destination, **sources, _migration=True)
                mark_committed()
                shutil.rmtree(backup)
        require(os.path.lexists(selected), 'DevTools migration lost both original and selection')
        if os.path.lexists(pending):
            require(pending.is_symlink() and os.readlink(pending) == str(modules),
                    'invalid pending DevTools selection')
            pending.unlink()
        marker.unlink()
    if selected.is_symlink():
        require(os.readlink(selected) == str(modules), 'DevTools modules select another prefix')
        return verify(source, protobuf, destination, **sources)
    require(not os.path.lexists(backup) and not os.path.lexists(pending),
            'unexpected DevTools migration files')
    verify(source, protobuf, destination, **sources, _legacy_devtools=True)
    require(selected.is_dir() and not selected.is_symlink(), 'legacy DevTools modules missing')
    with marker.open('x') as f:
        f.write('devtools-modules-v1\n')
    try:
        pending.symlink_to(modules, target_is_directory=True)
        selected.rename(backup)
        pending.rename(selected)
        verify(source, protobuf, destination, **sources, _migration=True)
    except BaseException:
        if os.path.lexists(backup):
            if selected.is_symlink() and os.readlink(selected) == str(modules):
                selected.unlink()
            if not os.path.lexists(selected):
                backup.rename(selected)
        if pending.is_symlink() and os.readlink(pending) == str(modules):
            pending.unlink()
        if not os.path.lexists(backup):
            marker.unlink(missing_ok=True)
        raise
    mark_committed()
    shutil.rmtree(backup)
    marker.unlink()
    return destination / 'src'


def sibling_component_transaction(destination, origin, names, identity, label, verify_old, build_new, verify_new,
                                  *, check_old_entry=None, already_new=None):
    """Swap verified sibling views under the caller's exclusive source lock."""
    import json
    import shutil
    require(names and len(names) == len(set(names)) and all(re.fullmatch(r'[A-Za-z0-9_.-]+', n) for n in names),
            'invalid component transaction names')
    require(re.fullmatch(r'[a-z0-9-]+', label), 'invalid component transaction label')
    selected = destination / 'src/third_party'
    if check_old_entry is None:
        check_old_entry = lambda path, name, partial: (path.is_symlink() and os.readlink(path) == str(origin / name))
    if already_new is None:
        already_new = lambda: all((selected / name).is_dir() and not (selected / name).is_symlink() for name in names)
    stage = destination.parent / ('.' + destination.name + '.' + label + '-stage')
    marker = destination.parent / ('.' + destination.name + '.' + label + '-migration')

    def mark(state):
        data = json.dumps({'version': 1, 'state': state, 'identity': identity}, sort_keys=True) + '\n'
        _write_transaction_marker(marker, data)

    def clean_stage(state):
        if os.path.lexists(stage):
            require(stage.is_dir() and not stage.is_symlink(), 'invalid common component stage')
            prefix = 'old-' if state == 'committed' else 'new-'
            for item in stage.iterdir():
                require(item.name in {prefix + name for name in names},
                        'unexpected common component stage entry')
                if state == 'committed':
                    require(check_old_entry(item, item.name[len(prefix):], True),
                            'invalid saved component during cleanup')
                else:
                    require(item.is_dir() and not item.is_symlink(), 'invalid staged common component')
            shutil.rmtree(stage)

    if os.path.lexists(marker):
        require(marker.is_file() and not marker.is_symlink(), 'invalid common component marker')
        record = json.loads(marker.read_text())
        require(record.get('version') == 1 and record.get('identity') == identity and
                record.get('state') in ('staging', 'prepared', 'committed', 'rolled-back'),
                'common component migration selection changed')
        if record['state'] == 'committed':
            verify_new(True)
        elif record['state'] == 'prepared':
            require(stage.is_dir() and not stage.is_symlink(), 'missing common component stage')
            for name in reversed(names):
                old, new, path = stage / ('old-' + name), stage / ('new-' + name), selected / name
                if os.path.lexists(old):
                    require(check_old_entry(old, name, False), 'invalid saved component')
                    if os.path.lexists(path):
                        require(path.is_dir() and not path.is_symlink() and not os.path.lexists(new),
                                'invalid partially installed common component')
                        path.rename(new)
                    old.rename(path)
                else:
                    require(check_old_entry(path, name, False), 'invalid original component')
            mark('rolled-back')
        clean_stage('committed' if record['state'] == 'committed' else 'rolled-back')
        marker.unlink()
        if record['state'] == 'committed':
            return destination / 'src'

    require(not os.path.lexists(stage), 'unexpected existing common component stage')
    if already_new():
        return verify_new(False)
    verify_old()
    mark('staging')
    stage.mkdir()
    try:
        for name in names:
            path = stage / ('new-' + name)
            build_new(name, path)
        mark('prepared')
    except BaseException:
        if not os.path.lexists(marker):
            clean_stage('staging')
        raise
    try:
        for name in names:
            path = selected / name
            require(check_old_entry(path, name, False), 'component changed before installation')
            path.rename(stage / ('old-' + name))
            (stage / ('new-' + name)).rename(path)
        verify_new(True)
        mark('committed')
    except BaseException:
        # Keep the prepared marker and stage for deterministic recovery on retry.
        raise
    clean_stage('committed')
    marker.unlink()
    return destination / 'src'


def activate_common_components(source, protobuf, destination, **sources):
    """Replace verified bundled component links with selected common views under lock."""
    import hashlib
    import json
    import shutil

    destination = Path(destination).resolve(strict=True)
    require(not os.path.lexists(destination.parent / ('.' + destination.name + '.devtools-modules-migration')),
            'another source-view transaction is incomplete')
    origin = Path(source).resolve(strict=True) / 'third_party'
    selected = destination / 'src/third_party'
    names = [name for name, enabled in (('abseil-cpp', sources.get('system_abseil')),
             ('icu', sources.get('system_icu')), ('re2', sources.get('system_re2')),
             ('protobuf', protobuf is not None)) if enabled]
    require(names, 'no common components selected')
    marker = destination.parent / ('.' + destination.name + '.common-components-migration')
    stage = destination.parent / ('.' + destination.name + '.common-components-stage')
    if not os.path.lexists(marker) and all((selected/name).is_dir() and not (selected/name).is_symlink() for name in names):
        require(not os.path.lexists(stage), 'unexpected existing common component stage')
        return _refresh_leaves(Path(source).resolve(strict=True), protobuf, destination, sources)
    require(not os.path.lexists(_refresh_marker(destination)), 'source view refresh is incomplete')
    identity = hashlib.sha256(json.dumps({'names': names, 'protobuf': str(protobuf),
        'protoc': str(sources.get('protobuf_protoc'))}, sort_keys=True).encode()).hexdigest()

    def verify_old():
        old_sources = dict(sources, system_abseil=False, system_icu=False, system_re2=False,
                           protobuf_protoc=None)
        _refresh_leaves(Path(source).resolve(strict=True), None, destination, old_sources)
        verify(source, None, destination, **old_sources)

    def verify_new(migration):
        return verify(source, protobuf, destination, **sources, _migration=migration)

    def build_new(name, path):
        if name == 'protobuf':
            common = {'src', 'third_party'} | ({'python'} if sources.get('protobuf_protoc') else set())
            path.mkdir()
            for entry, item in entries(origin / name, common).items():
                (path / entry).symlink_to(item, target_is_directory=item.is_dir())
            for entry in ('src', 'third_party'):
                (path / entry).symlink_to(Path(protobuf).resolve(strict=True) / entry, target_is_directory=True)
            if sources.get('protobuf_protoc'):
                python_view(Path(protobuf), path / 'python', sources['protobuf_protoc'])
        else:
            replacements = {'abseil-cpp': abseil_replacements, 'icu': icu_replacements,
                            're2': re2_replacements}[name](Path(source))
            masks = abseil_masks(Path(source), replacements) if name == 'abseil-cpp' else shim_masks(replacements)
            dependency_view(origin / name, path, replacements, masks)

    return sibling_component_transaction(destination, origin, names, identity, 'common-components',
                                         verify_old, build_new, verify_new)


def refresh(source, protobuf, destination, **sources):
    """Recompose generated inputs while keeping the sibling Ninja output intact.

    The caller must hold the workspace/output locks and verify prepared sources
    and compiler/provider identity before requesting this operation.
    """
    import tempfile

    destination = Path(destination)
    require(destination.is_absolute(), 'source view destination must be absolute')
    resolved = destination.resolve()
    marker = _refresh_marker(destination)
    if os.path.lexists(marker):
        require(stat.S_ISREG(os.lstat(marker).st_mode) and
                marker.read_text() == 'source-view-leaves-v1\n',
                'invalid source view refresh marker')
    source = Path(source).resolve(strict=True)
    require((source / '.gn').is_file(), 'incomplete Electron source')
    if protobuf is not None:
        require((source / 'third_party/protobuf').is_dir() and
                (Path(protobuf) / 'src').is_dir() and
                (Path(protobuf) / 'third_party').is_dir(), 'incomplete common Protobuf source')
    if sources.get('v8') is not None:
        v8 = Path(sources['v8']).resolve(strict=True)
        require((v8 / 'BUILD.gn').is_file() and (v8 / 'include/v8-version.h').is_file(),
                'incomplete common V8 source')
    for name, provider_marker in (('node', 'node.gni'), ('perfetto', 'gn/perfetto.gni')):
        if sources.get(name) is not None:
            provider = Path(sources[name]).resolve(strict=True)
            require((provider / provider_marker).is_file(), 'incomplete common source: ' + name)
    for value in (source, protobuf, *(sources.get(name) for name in
                  ('node', 'perfetto', 'v8', 'node_modules'))):
        if value is not None:
            origin = Path(value).resolve(strict=True)
            require(not resolved.is_relative_to(origin) and
                    not origin.is_relative_to(resolved), 'source view overlaps an input')
    existing = os.path.lexists(destination)
    if existing:
        require(destination.is_dir() and not destination.is_symlink(),
                'source view must be a local directory')
        require({p.name for p in destination.iterdir()} == {'src'},
                'unexpected entries outside generated source view')
        require((destination / 'src').is_dir() and not (destination / 'src').is_symlink(),
                'source view src must be a local directory')
        local_out = destination / 'src/out'
        require(local_out.is_dir() and not local_out.is_symlink() and
                not any(local_out.iterdir()),
                'source view contains build outputs; use the sibling work/out directory')
    if existing:
        try:
            return _refresh_leaves(source, protobuf, destination, sources)
        except _LayoutChanged:
            pass
    with tempfile.TemporaryDirectory(prefix='.source-view-refresh-',
                                     dir=destination.parent) as temporary:
        scratch = Path(temporary)
        candidate = scratch / 'candidate'
        create(source, protobuf, candidate, **sources)
        verify(source, protobuf, candidate, **sources)
        previous = scratch / 'previous'
        if existing:
            destination.rename(previous)
        try:
            candidate.rename(destination)
        except BaseException:
            if existing:
                previous.rename(destination)
            raise
    marker = _refresh_marker(destination)
    if os.path.lexists(marker):
        require(stat.S_ISREG(os.lstat(marker).st_mode) and
                marker.read_text() == 'source-view-leaves-v1\n',
                'invalid source view refresh marker')
        marker.unlink()
    return destination / 'src'
