# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Build a stable local view of a verified common source subtree."""
import hashlib
import os
from pathlib import Path
import shutil
import stat


def prepare_projection(inventory, old_root, common_root, destination, *, old_aliases=(),
                       sourceprep=None, package=None, identity=None):
    """Create a new projection preserving timestamps only for identical files.

    The caller owns the source/view lock, has verified the common source, and
    stages this directory in the owning source-view transaction. Unchanged
    provider identities are handled by the caller without invoking this walk.
    """
    common = Path(common_root).resolve(strict=True)
    old = Path(old_root).resolve(strict=True) if old_root is not None else None
    requested = Path(destination)
    if not requested.is_absolute() or requested.name in ('', '.', '..'):
        raise ValueError('ML projection destination must be new and absolute')
    dest = requested.parent.resolve(strict=True) / requested.name
    if os.path.lexists(dest):
        raise ValueError('ML projection destination must be new and absolute')
    if any(dest.is_relative_to(path) or path.is_relative_to(dest) for path in (common, *([old] if old else []))):
        raise ValueError('ML projection overlaps source inputs')
    aliases = []
    for prefix, root in old_aliases:
        prefix = Path(prefix)
        if prefix.is_absolute() or '..' in prefix.parts:
            raise ValueError('invalid ML source alias prefix')
        root = Path(root).resolve(strict=True)
        if dest.is_relative_to(root) or root.is_relative_to(dest):
            raise ValueError('ML projection overlaps source alias')
        aliases.append((prefix, root, inventory.snapshot_tree(str(root))))
    new_rows = inventory.snapshot_tree(str(common), exclude=('emberbsd-prepared-source.json',))
    old_rows = inventory.snapshot_tree(str(old)) if old else {}
    dest.mkdir()
    try:
        for relative, row in sorted(new_rows.items(), key=lambda item: (len(Path(item[0]).parts), item[0])):
            output = dest / relative
            if row['kind'] == 'directory':
                output.mkdir(mode=0o700)
            elif row['kind'] == 'file':
                source = common / relative
                previous = old / relative if old else None
                equal = previous is not None and old_rows.get(relative) == row
                old_times = []
                for prefix, alias_root, alias_rows in aliases:
                    rel = Path(relative)
                    if rel.is_relative_to(prefix):
                        alias_rel = rel.relative_to(prefix).as_posix()
                        alias_file = alias_root / alias_rel
                        if alias_rel not in alias_rows:
                            continue
                        if alias_rows[alias_rel] != row:
                            equal = False
                        else:
                            before_alias = os.lstat(alias_file)
                            if inventory.sha256_file(str(alias_file)) != row['sha256']:
                                raise ValueError('ML alias changed since inventory: ' + str(alias_file))
                            inventory.verify_stable(str(alias_file), before_alias)
                            old_times.append(before_alias.st_mtime_ns)
                selected = previous if equal else source
                handle, before = inventory.open_regular(str(selected))
                digest = hashlib.sha256()
                with handle, output.open('xb') as target:
                    while chunk := handle.read(1024 * 1024):
                        digest.update(chunk)
                        target.write(chunk)
                    if inventory.stable_identity(os.fstat(handle.fileno())) != inventory.stable_identity(before):
                        raise ValueError('ML source changed during copy: ' + str(selected))
                inventory.verify_stable(str(selected), before)
                if digest.hexdigest() != row['sha256'] or before.st_size != row['size'] or stat.S_IMODE(before.st_mode) != row['mode']:
                    raise ValueError('ML source changed since inventory: ' + str(selected))
                os.chmod(output, row['mode'])
                if equal:
                    os.utime(output, ns=(before.st_atime_ns, min([before.st_mtime_ns, *old_times])))
            elif row['kind'] == 'link':
                os.symlink(row['target'], output)
            else:
                raise ValueError('unsupported ML source entry')
        for relative, row in sorted(new_rows.items(), key=lambda item: -len(Path(item[0]).parts)):
            if row['kind'] == 'directory':
                os.chmod(dest / relative, row['mode'])
        os.chmod(dest, stat.S_IMODE(os.stat(common).st_mode))
        if sourceprep is not None:
            sourceprep.write_prepared_tree_receipt(str(dest), package=package, identity=identity)
    except BaseException:
        shutil.rmtree(dest)
        raise
    return dest


def validate_projection(sourceprep, destination, *, package, identity):
    """Reuse a projection with the SDK prepared-tree cache and unchanged inputs."""
    return sourceprep.validate_prepared_tree(str(destination), package=package, identity=identity)


def prepare_selected_projection(inventory, old_root, files, destination, *, sourceprep, package, identity):
    """Project only package-owned installed files and verify their pkgdb MD5."""
    old = Path(old_root).resolve(strict=True) if old_root is not None else None
    requested = Path(destination)
    if not requested.is_absolute() or requested.name in ('', '.', '..'):
        raise ValueError('header projection destination must be new and absolute')
    dest = requested.parent.resolve(strict=True) / requested.name
    if os.path.lexists(dest) or (old and (dest.is_relative_to(old) or old.is_relative_to(dest))):
        raise ValueError('header projection destination overlaps an input')
    if not files:
        raise ValueError('header projection is empty')
    dest.mkdir()
    try:
        for relative, record in sorted(files.items()):
            rel = Path(relative)
            if rel.is_absolute() or not rel.parts or '..' in rel.parts:
                raise ValueError('invalid selected header path')
            source = Path(record['path'])
            if not source.is_absolute():
                raise ValueError('selected header source is not absolute')
            output = dest/rel
            output.parent.mkdir(parents=True, exist_ok=True)
            handle, before = inventory.open_regular(str(source))
            if list(inventory.stable_identity(before)) != list(record['stable']):
                handle.close()
                raise ValueError('selected header changed before copying: ' + str(source))
            sha256, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
            with handle, output.open('xb') as target:
                while chunk := handle.read(1024*1024):
                    sha256.update(chunk); md5.update(chunk); target.write(chunk)
                if inventory.stable_identity(os.fstat(handle.fileno())) != inventory.stable_identity(before):
                    raise ValueError('selected header changed during copying: ' + str(source))
            inventory.verify_stable(str(source), before)
            if md5.hexdigest() != record['md5']:
                raise ValueError('selected header differs from package checksum: ' + str(source))
            os.chmod(output, stat.S_IMODE(before.st_mode))
            previous = old/rel if old else None
            if previous and previous.is_file() and not previous.is_symlink():
                previous_info = os.lstat(previous)
                if (stat.S_IMODE(previous_info.st_mode) == stat.S_IMODE(before.st_mode) and
                        previous_info.st_size == before.st_size and
                        inventory.sha256_file(str(previous)) == sha256.hexdigest()):
                    inventory.verify_stable(str(previous), previous_info)
                    os.utime(output, ns=(previous_info.st_atime_ns, previous_info.st_mtime_ns))
        sourceprep.write_prepared_tree_receipt(str(dest), package=package, identity=identity)
    except BaseException:
        shutil.rmtree(dest)
        raise
    return dest
