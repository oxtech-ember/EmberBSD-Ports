#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify and prepare an incremental pkgsrc stage patch refresh.

This module never accepts an unverified old patch list or a caller-supplied
replacement digest. The controlling owner holds the stage lock for its lifetime.
The explicit configure-aware mode binds a previous Makefile to installed
provenance and supports one added pre-configure SUBST class whose literal files
are exactly the added patch targets. Unchanged patch hooks must be bounded
timestamp copies. The selected pkgsrc SUBST generates the verified candidate
and records a verified no-op in the live stage before the journal is cleared.
The previous-recipe mode binds complete old patch inputs to the installed
package, replays replacement patches and an unchanged existing SUBST class,
and verifies omitted old-cookie targets without rewriting their source files.
"""
import base64
import hashlib
from functools import lru_cache
import os
from pathlib import Path, PurePosixPath
import re
import stat

MAX_STAGE_ARCHIVE_BYTES = 512 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stable_read(paths, path):
    handle, before = paths.open_regular(str(path))
    with handle:
        data = handle.read()
        require(paths.stable_identity(os.fstat(handle.fileno())) == paths.stable_identity(before),
                'file changed while reading: ' + str(path))
    paths.verify_stable(str(path), before)
    return data


@lru_cache(maxsize=4)
def active_parse_trace(command):
    """Read the selected bmake parse trace once per immutable invocation."""
    import subprocess
    result = subprocess.run(list(command) + ['-d', 'p', '-V', 'PKGNAME'], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    require(bool(result.stdout.strip()), 'unsupported bmake patch parse trace: missing package identity')
    return result.stderr


def validate_active_target(paths, command, recipe, makefiles, framework_files, target,
                           *, previous_recipe=None, observed=None):
    """Reject active non-framework target rules, including dependencies."""
    import shlex
    sources = [(Path(item) if Path(item).is_absolute() else recipe / item)
               for item in shlex.split(makefiles)]
    framework_files = set(framework_files)
    if previous_recipe is not None:
        current_root = recipe.parents[1].resolve()
        previous_root = previous_recipe.parents[1].resolve()
        loaded = {source.resolve() for source in sources}
        for current in tuple(framework_files):
            previous = previous_root / current.relative_to(current_root)
            if previous == current or previous.resolve() not in loaded:
                continue
            require(previous.resolve() == previous, 'previous framework path is not canonical')
            current_data, previous_data = stable_read(paths, current), stable_read(paths, previous)
            require(previous_data == current_data, 'previous framework differs: ' + str(previous))
            # Keep both identities in the transaction's existing drift guard.
            require(observed is not None, 'previous framework requires input observation')
            for path, data in ((current, current_data), (previous, previous_data)):
                require(path not in observed or observed[path] == data,
                        'framework input changed during verification: ' + str(path))
                observed[path] = data
            framework_files.add(previous)
    potential = False
    for source in sources:
        if (source.resolve() not in framework_files and
                re.search(rb'(?m)^\s*' + re.escape(target.encode()) + rb'\s*:', stable_read(paths, source))):
            potential = True
    if not potential:
        return
    trace = active_parse_trace(tuple(command))
    origin = None
    found = 0
    for line in trace.splitlines():
        if line.startswith('Parsing '):
            match = re.fullmatch(r'Parsing (.+):([0-9]+): (.*)', line)
            require(match is not None, 'unsupported bmake patch parse trace: invalid source origin')
            path = Path(match.group(1))
            origin = (path if path.is_absolute() else recipe / path).resolve()
        elif line.startswith('ParseDependency('):
            match = re.fullmatch(r'ParseDependency\((.*)\)', line)
            require(match is not None and origin is not None,
                    'unsupported bmake patch parse trace: missing dependency origin')
            left, sep, _ = match.group(1).partition(':')
            require(bool(sep), 'unsupported bmake patch parse trace: invalid dependency')
            if target in left.split():
                require(origin in framework_files, 'active custom ' + target + ' is unsupported')
                found += 1
    require(found == 1, 'unsupported bmake patch parse trace: framework ' + target + ' not uniquely identified')


def targets(data):
    """Return patch targets, rejecting renames, deletion and unsafe paths."""
    lines = data.splitlines()
    result = set()
    for i, line in enumerate(lines[:-1]):
        if not line.startswith(b'--- ') or not lines[i + 1].startswith(b'+++ '):
            continue
        before = line[4:].split()[0]
        after = lines[i + 1][4:].split()[0]
        require(after != b'/dev/null', 'patch deletion is unsupported')
        try:
            name = after.decode('ascii')
        except UnicodeError as exc:
            raise ValueError('non-ASCII patch path') from exc
        parts = PurePosixPath(name).parts
        require(name and not name.startswith('/') and '\\' not in name and
                all(p not in ('', '.', '..') for p in name.split('/')) and
                all(ord(c) >= 32 and ord(c) != 127 for c in name), 'unsafe patch path')
        if before != b'/dev/null':
            previous = before.decode('ascii').removesuffix('.orig')
            require(previous == name, 'patch rename is unsupported')
        result.add('/'.join(parts))
    require(result, 'patch has no supported file targets')
    return result


def validate_patch_endpoints(paths, tree, data):
    """Reject link/special patch targets and backups before executing patch."""
    lines = data.splitlines()
    found = False
    for index, line in enumerate(lines[:-1]):
        if not line.startswith(b'--- ') or not lines[index + 1].startswith(b'+++ '):
            continue
        found = True
        for field in (line[4:].split()[0], lines[index + 1][4:].split()[0]):
            if field == b'/dev/null':
                continue
            try:
                name = field.decode('ascii')
            except UnicodeError as exc:
                raise ValueError('non-ASCII patch path') from exc
            parts = name.split('/')
            require(name and not name.startswith('/') and '\\' not in name and
                    all(part not in ('', '.', '..') for part in parts) and
                    all(ord(c) >= 32 and ord(c) != 127 for c in name),
                    'unsafe patch path')
            # Both header spellings and the backup names may be inspected by
            # patch; check each without ever following an archive symlink.
            for candidate in {name, name.removesuffix('.orig')}:
                for endpoint in (candidate, candidate + '.orig'):
                    current = tree
                    pieces = endpoint.split('/')
                    for part in pieces[:-1]:
                        current /= part
                        if paths.entry(str(current)) is None:
                            break
                        paths.real_directory(str(current))
                    else:
                        current /= pieces[-1]
                        if paths.entry(str(current)) is not None:
                            paths.regular_file(str(current))
    require(found, 'patch has no supported file headers')


def unselected_subst_file(paths, root, name):
    """Return whether a literal input exists; reject links and special files."""
    current = root
    parts = name.split('/')
    for index, part in enumerate(parts):
        current = current / part
        if paths.entry(str(current)) is None:
            return False
        if index == len(parts) - 1:
            paths.regular_file(str(current))
        else:
            paths.real_directory(str(current))
    return True


def unselected_subst_pattern(paths, roots, pattern, changed):
    """Check a bounded glob without following links or touching changed leaves."""
    import fnmatch

    def component_matches(name, component):
        return (not name.startswith('.') or component.startswith('.')) and fnmatch.fnmatchcase(name, component)

    parts = pattern.split('/')
    require(parts and all(re.fullmatch(r'[A-Za-z0-9_+.*?-]+', part) and
                          part not in ('.', '..') and '**' not in part for part in parts),
            'unsupported substitution paths')
    for name in changed:
        leaf = name.split('/')
        require(len(leaf) != len(parts) or
                not all(component_matches(value, match) for value, match in zip(leaf, parts)),
                'changed source needs substitution refresh')

    def walk(fd, index):
        component = parts[index]
        if '*' in component or '?' in component:
            with os.scandir(fd) as entries:
                names = sorted(entry.name for entry in entries
                               if component_matches(entry.name, component))
        else:
            names = [component]
        for name in names:
            try:
                before = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                if '*' in component or '?' in component:
                    raise ValueError('substitution match changed during inspection: ' + name)
                continue
            if index + 1 == len(parts):
                require(stat.S_ISREG(before.st_mode), 'expected a regular substitution match: ' + name)
                flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
                child = os.open(name, flags, dir_fd=fd)
                try:
                    require(paths.stable_identity(os.fstat(child)) == paths.stable_identity(before),
                            'substitution match changed during inspection: ' + name)
                finally:
                    os.close(child)
            elif stat.S_ISREG(before.st_mode):
                # A regular file cannot be an ancestor of a matched path.
                continue
            else:
                require(stat.S_ISDIR(before.st_mode), 'unsafe substitution ancestor: ' + name)
                flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_DIRECTORY', 0)
                child = os.open(name, flags, dir_fd=fd)
                try:
                    require(paths.stable_identity(os.fstat(child)) == paths.stable_identity(before),
                            'substitution ancestor changed during inspection: ' + name)
                    walk(child, index + 1)
                finally:
                    os.close(child)
            require(paths.stable_identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) ==
                    paths.stable_identity(before), 'substitution match changed during inspection: ' + name)

    for root in roots:
        before = paths.real_directory(str(root))
        fd = os.open(root, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_DIRECTORY', 0))
        try:
            require(paths.stable_identity(os.fstat(fd)) == paths.stable_identity(before),
                    'substitution root changed during inspection')
            walk(fd, 0)
            require(paths.stable_identity(os.fstat(fd)) == paths.stable_identity(before),
                    'substitution root changed during inspection')
            paths.verify_stable(str(root), before)
        finally:
            os.close(fd)


def old_metadata(paths, recipe, work, installed_version, old_cookie=None, *, previous_recipe=None):
    """Bind the old ordered cookie to installed BUILD_VERSION and current recipe."""
    cookie = stable_read(paths, work / '.patch_done') if old_cookie is None else old_cookie
    try:
        old_paths = [Path(s) for s in cookie.decode('utf-8').splitlines() if s]
    except UnicodeError as exc:
        raise ValueError('invalid old patch cookie') from exc
    patchdir = (recipe / 'patches').resolve(strict=True)
    cookie_roots = {patchdir}
    if previous_recipe is not None:
        previous_patches = Path(previous_recipe) / 'patches'
        require(previous_patches.is_absolute() and
                previous_patches.resolve(strict=True) == previous_patches,
                'previous patch directory is not canonical')
        cookie_roots.add(previous_patches)
    require(all(p.is_absolute() and p.resolve(strict=True) == p and
                p.parent in cookie_roots for p in old_paths),
            'old patch cookie contains an unsupported path')
    # The explicit previous directory only identifies cookie origins. Its
    # complete recipe and patch inventory must still match installed provenance.
    old = [p.name for p in old_paths]
    require(len(set(old)) == len(old), 'duplicate old patch')
    version = stable_read(paths, installed_version).decode('utf-8')
    records = {}
    for line in version.splitlines():
        if ': ' not in line:
            continue
        key, value = line.rsplit(': ', 1)
        require(re.fullmatch(r'[0-9a-f]{64}', value), 'invalid BUILD_VERSION hash')
        normalized = os.path.normpath(key)
        require(normalized not in records, 'duplicate BUILD_VERSION entry')
        records[normalized] = value
    pkgpath = '/'.join(recipe.parts[-2:])
    if not old:
        require(not any(key.startswith(pkgpath + '/patches/patch-') for key in records),
                'empty patch cookie contradicts installed patch provenance')
    new = sorted(p.name for p in patchdir.glob('patch-*') if p.is_file())
    old_recipe = Path(previous_recipe) if previous_recipe is not None else recipe
    if previous_recipe is not None:
        require(old_recipe.is_absolute(), 'previous recipe must be absolute')
        for name in ('Makefile', 'distinfo'):
            require(records.get(pkgpath + '/' + name) ==
                    hashlib.sha256(stable_read(paths, old_recipe / name)).hexdigest(),
                    'previous recipe identity changed: ' + name)
        complete = sorted(p.name for p in (old_recipe / 'patches').glob('patch-*') if p.is_file())
        recorded_prefix = pkgpath + '/patches/'
        recorded = sorted(key[len(recorded_prefix):] for key in records
                          if key.startswith(recorded_prefix + 'patch-'))
        require(complete == recorded, 'previous recipe patch inventory differs from installed provenance')
        require([name for name in complete if name in old] == old,
                'old patch cookie is not an ordered subsequence of previous recipe')
        # A completed build may retain an earlier extraction/patch cookie.
        # Reconcile it only against the complete installed recipe; prepare()
        # adds mandatory live preimage checks for every omitted patch target.
        old = complete
    require([p for p in new if p in old] == old and
            (previous_recipe is not None or len(new) > len(old)),
            'old patch list is not a proper subsequence')
    for name in old:
        expected = records.get(pkgpath + '/patches/' + name)
        require(expected and hashlib.sha256(stable_read(paths, old_recipe / 'patches' / name)).hexdigest() == expected,
                'old patch identity changed: ' + name)
    additions = [p for p in new if p not in old]
    distinfo = stable_read(paths, recipe / 'distinfo')
    old_distinfo = (stable_read(paths, old_recipe / 'distinfo') if previous_recipe is not None else
                    b''.join(line for line in distinfo.splitlines(keepends=True)
                             if not any(line.startswith(b'SHA1 (' + name.encode() + b') = ') for name in additions)))
    expected = records.get(pkgpath + '/distinfo')
    require(expected and hashlib.sha256(old_distinfo).hexdigest() == expected,
            'old distinfo cannot be reconstructed exactly')
    return old, new, additions, cookie


def prepare(sdk, recipe, work, archive, archive_root, installed_version, patch, patch_args, scratch, *, old_cookie=None, transform=None, allow_completed=False, previous_recipe=None, old_transform=None):
    """Replay complete old and current patch order and return validated leaf changes."""
    paths, sourceprep, archive_metadata = sdk['paths'], sdk['sourceprep'], sdk['archive_metadata']
    recipe, work, archive, scratch = map(Path, (recipe, work, archive, scratch))
    old, new, additions, old_cookie = old_metadata(paths, recipe, work, installed_version, old_cookie, previous_recipe=previous_recipe)
    metadata, patches = archive_metadata.read_recipe(recipe, archive.name, archive_root)
    if previous_recipe is not None:
        old_recipe = Path(previous_recipe)
        old_meta, old_patches = archive_metadata.read_recipe(old_recipe, archive.name, archive_root)
        require([p.name for p in old_patches] == old, 'previous recipe patch inventory changed')
    else:
        old_recipe, old_meta = recipe, metadata
    data = stable_read(paths, archive)
    measured = sourceprep.archive_hashes(data)
    require(all(measured[k] == old_meta[k] for k in ('sha512', 'blake2s', 'size')),
            'archive differs from previous distinfo')
    require(all(measured[k] == metadata[k] for k in ('sha512', 'blake2s', 'size')),
            'archive differs from verified distinfo')
    require([p.name for p in patches] == new, 'current patch inventory changed')
    require(patch_args == ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'],
            'unsupported selected pkgsrc PATCH_ARGS')
    affected = set()
    cookie_inventory = {Path(name).name for name in old_cookie.decode('utf-8').splitlines() if name}
    verify_targets = set()
    for name in old:
        if name not in cookie_inventory:
            verify_targets.update(targets(stable_read(paths, old_recipe / 'patches' / name)))
    for name in new:
        current = stable_read(paths, recipe / 'patches' / name)
        prior = stable_read(paths, old_recipe / 'patches' / name) if name in old else None
        if prior != current:
            affected.update(targets(current))
            if prior is not None:
                affected.update(targets(prior))
    candidates = []
    for label, series in (('old', old), ('new', new)):
        dest = scratch / label
        dest.mkdir()
        require(getattr(sourceprep, 'ARCHIVE_INTERNAL_SYMLINKS_API', None) == 1,
                'selected SDK lacks verified internal symlink extraction')
        sourceprep.extract_archive(archive, dest, archive_root, label,
                                   internal_symlinks=True,
                                   max_bytes=MAX_STAGE_ARCHIVE_BYTES)
        tree = dest / archive_root
        for name in series:
            path = (old_recipe if label == 'old' else recipe) / 'patches' / name
            contents = stable_read(paths, path)
            patch_meta = old_meta if label == 'old' else metadata
            require(hashlib.sha256(contents).hexdigest() == patch_meta['recipe']['patches/' + name],
                    'patch changed during replay: ' + name)
            validate_patch_endpoints(paths, tree, contents)
            sourceprep.apply_patch(str(patch), path, contents, tree, label,
                                   patch_args=tuple(patch_args), allow_dev_null=True)
            require(stable_read(paths, path) == contents, 'patch changed while applying: ' + name)
        candidates.append(tree)
    if old_transform is not None:
        old_transform(candidates[0], affected)
    if transform is not None:
        transform(candidates[1], affected)
    require(sourceprep.archive_hashes(stable_read(paths, archive)) == measured,
            'archive changed during replay')
    changes = []
    adoption_states = set()
    for name in sorted(affected | verify_targets):
        before, after = (tree / name for tree in candidates)
        require(not before.is_symlink() and not after.is_symlink(), 'symlink patch target')
        old_data = stable_read(paths, before) if before.is_file() else None
        new_data = stable_read(paths, after) if after.is_file() else None
        if name in verify_targets:
            require(old_data is not None, 'omitted patch has no verifiable installed preimage: ' + name)
        require(new_data is not None, 'patch deletion or nonregular result is unsupported')
        old_mode = stat.S_IMODE(before.stat().st_mode) if old_data is not None else None
        new_mode = stat.S_IMODE(after.stat().st_mode)
        if old_data is not None:
            # SDK archive preparation normalizes permissions to 0644/0755.
            # pkgsrc preserves the archive's full mode; patches do not encode
            # mode changes, so retain the verified live mode on replacement.
            require(old_mode == new_mode, 'patch changes normalized file mode')
            live = work / archive_root / name
            live_mode = stat.S_IMODE(paths.regular_file(str(live)).st_mode)
            require((live_mode & 0o111) == (old_mode & 0o111), 'live executable bits differ: ' + name)
            old_mode = live_mode
            new_mode = live_mode
        if old_data != new_data or old_mode != new_mode or name in verify_targets:
            if allow_completed:
                require(old_data is not None, 'configured refresh requires existing patch targets')
                marker = work / '.emberbsd-patch-refresh.json'
                if marker.exists():
                    record = sdk['jsonio'].read_json(str(marker))
                    rows = [row for row in record.get('files', []) if row.get('name') == name]
                    require(len(rows) == 1 and rows[0].get('old_sha') in (_sha(old_data), _sha(new_data)),
                            'invalid adopted patch preimage: ' + name)
                    if rows[0]['old_sha'] == _sha(new_data):
                        old_data = new_data
                else:
                    live_data = stable_read(paths, work / archive_root / name)
                    require(live_data in (old_data, new_data), 'live preimage differs: ' + name)
                    if live_data == new_data:
                        adoption_states.add('new')
                        old_data = new_data
                    else:
                        adoption_states.add('old')
            changes.append((name, old_data, new_data, old_mode, new_mode))
    require(len(adoption_states) <= 1, 'mixed configured patch preimages')
    require(changes, 'patch series has no source changes or inventory reconciliation')
    return changes, old_cookie, new


def _sha(data):
    return hashlib.sha256(data).hexdigest()



def journal_old_cookie(sdk, work):
    """Return journal cookie bytes; caller must revalidate against installed provenance."""
    marker = Path(work) / '.emberbsd-patch-refresh.json'
    record = sdk['jsonio'].read_json(str(marker))
    require(isinstance(record, dict) and record.get('version') == 1 and
            isinstance(record.get('old_cookie_b64'), str), 'invalid patch refresh journal')
    try:
        value = base64.b64decode(record['old_cookie_b64'], validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError('invalid journal cookie encoding') from exc
    require(record.get('old_cookie') == _sha(value), 'journal cookie digest changed')
    return value

def _entry(paths, root, name):
    require(name and not name.startswith('/') and '\\' not in name and
            all(part not in ('', '.', '..') for part in name.split('/')), 'unsafe journal path')
    path = root.joinpath(*name.split('/'))
    current = root
    for component in name.split('/')[:-1]:
        current = current / component
        paths.real_directory(str(current))
    require(path.parent.resolve(strict=True).is_relative_to(root), 'patch target escapes stage')
    return path


def _write_exclusive(path, data, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), mode)
    with os.fdopen(fd, 'wb') as out:
        os.fchmod(out.fileno(), mode)
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


def transaction(sdk, work, source, changes, old_cookie, new_inventory, build_clean, *, inject=None):
    """Commit validated leaves and owner cookie; preserve journal until build-clean succeeds.

    The caller must hold the same canonical stage lock as ordinary package stages.
    A crash is recovered forward; an ordinary pre-cookie error rolls back only
    files whose current bytes still match this transaction.
    """
    import shutil
    paths, jsonio = sdk['paths'], sdk['jsonio']
    paths.real_directory(str(work))
    paths.real_directory(str(source))
    work = Path(paths.canonical_existing(str(work)))
    source = Path(paths.canonical_existing(str(source)))
    require(source != work and source.is_relative_to(work), 'source is not inside work directory')
    marker, staging = work / '.emberbsd-patch-refresh.json', work / '.emberbsd-patch-refresh'
    cookie = work / '.patch_done'
    new_cookie = ''.join(str(p) + '\n' for p in new_inventory).encode()
    require(changes and len({row[0] for row in changes}) == len(changes), 'empty or duplicate patch changes')
    expected = [dict(index=i, name=name, old_sha=None if before is None else _sha(before),
                     new_sha=_sha(after), old_mode=old_mode, new_mode=new_mode)
                for i, (name, before, after, old_mode, new_mode) in enumerate(changes)]
    def step(label):
        if inject:
            inject(label)
    def read_or_none(path):
        if not os.path.lexists(path):
            return None
        return stable_read(paths, path)
    def check_stage(record):
        allowed = {'cookie-old', 'cookie-new', 'cookie-next'}
        for row in record['files']:
            index = str(row['index'])
            allowed.update(('old-' + index, 'new-' + index, 'restore-' + index))
            restore = staging / ('restore-' + index)
            if os.path.lexists(restore):
                require(row['old_sha'] is not None and _sha(stable_read(paths, restore)) == row['old_sha'] and
                        stat.S_IMODE(paths.regular_file(str(restore)).st_mode) == row['old_mode'],
                        'foreign patch restore candidate: ' + row['name'])
        if os.path.lexists(staging):
            paths.real_directory(str(staging))
            require({p.name for p in staging.iterdir()} <= allowed, 'unexpected patch refresh staging entry')
    def clean_stage(record):
        check_stage(record)
        if os.path.lexists(staging):
            shutil.rmtree(staging)
        step('stage-cleaned')
        marker.unlink()
    def rollback(record):
        conflicts = []
        for row in reversed(record['files']):
            path = _entry(paths, source, row['name'])
            current = read_or_none(path)
            current_mode = None if current is None else stat.S_IMODE(paths.regular_file(str(path)).st_mode)
            if (row['old_sha'] == row['new_sha'] and row['old_mode'] == row['new_mode'] and
                    current is not None and _sha(current) == row['old_sha'] and current_mode == row['old_mode']):
                continue
            if current is not None and _sha(current) == row['new_sha'] and current_mode == row['new_mode']:
                new = staging / ('new-' + str(row['index']))
                if not os.path.lexists(new):
                    _write_exclusive(new, changes[row['index']][2], row['new_mode'])
                if row['old_sha'] is None:
                    path.unlink()
                else:
                    old = staging / ('old-' + str(row['index']))
                    require(_sha(stable_read(paths, old)) == row['old_sha'], 'backup changed')
                    restore = staging / ('restore-' + str(row['index']))
                    if os.path.lexists(restore):
                        require(_sha(stable_read(paths, restore)) == row['old_sha'] and
                                stat.S_IMODE(paths.regular_file(str(restore)).st_mode) == row['old_mode'],
                                'foreign patch restore candidate: ' + row['name'])
                    else:
                        os.link(old, restore, follow_symlinks=False)
                    step('restore-link')
                    os.replace(restore, path)
            elif not ((current is None and row['old_sha'] is None) or
                      (current is not None and _sha(current) == row['old_sha'] and
                       current_mode == row['old_mode'])):
                conflicts.append(row['name'])
        if read_or_none(cookie) != old_cookie:
            conflicts.append('.patch_done')
        require(not conflicts, 'cannot roll back modified live inputs: ' + ', '.join(conflicts))
        record['phase'] = 'rolled-back'
        jsonio.write_json(str(marker), record, exclusive=False)
        clean_stage(record)
    if not os.path.lexists(marker):
        require(not os.path.lexists(staging), 'stray patch refresh stage')
        require(stable_read(paths, cookie) == old_cookie, 'old patch cookie changed')
        record = dict(version=1, source=str(source), files=expected, old_cookie=_sha(old_cookie),
                      old_cookie_b64=base64.b64encode(old_cookie).decode('ascii'),
                      new_cookie=_sha(new_cookie), phase='preparing')
        jsonio.write_json(str(marker), record)
        try:
            step('preparing-marker')
            os.mkdir(staging, 0o700)
            for index, (name, old, new, old_mode, new_mode) in enumerate(changes):
                path = _entry(paths, source, name)
                live = read_or_none(path)
                require(live == old, 'live preimage differs: ' + name)
                if live is not None:
                    current = paths.regular_file(str(path))
                    require(stat.S_IMODE(current.st_mode) == old_mode, 'live mode differs: ' + name)
                    backup = staging / ('old-' + str(index))
                    _write_exclusive(backup, old, old_mode)
                    os.utime(backup, ns=(current.st_atime_ns, current.st_mtime_ns))
                _write_exclusive(staging / ('new-' + str(index)), new, new_mode)
                step('preparing-file-' + str(index))
            _write_exclusive(staging / 'cookie-old', old_cookie, 0o600)
            _write_exclusive(staging / 'cookie-new', new_cookie, 0o600)
            record['phase'] = 'prepared'
            jsonio.write_json(str(marker), record, exclusive=False)
        except BaseException:
            if record['phase'] == 'preparing':
                clean_stage(record)
            raise
    else:
        record = jsonio.read_json(str(marker))
        require(isinstance(record, dict) and record.get('version') == 1 and
                record.get('source') == str(source) and
                record.get('phase') in ('preparing', 'prepared', 'cookie', 'complete', 'rolled-back') and
                isinstance(record.get('files'), list), 'foreign patch refresh journal')
        require(record.get('old_cookie') == _sha(old_cookie) and
                record.get('old_cookie_b64') == base64.b64encode(old_cookie).decode('ascii') and
                record.get('new_cookie') == _sha(new_cookie),
                'patch refresh journal identity changed')
        require(record['files'] == expected, 'patch refresh journal leaves changed')
        check_stage(record)
        if record['phase'] in ('preparing', 'complete', 'rolled-back'):
            complete = record['phase'] == 'complete'
            require(stable_read(paths, cookie) == (new_cookie if complete else old_cookie),
                    'finished patch cookie changed')
            for row in record['files']:
                path = _entry(paths, source, row['name'])
                live = read_or_none(path)
                expected_sha = row['new_sha'] if complete else row['old_sha']
                expected_mode = row['new_mode'] if complete else row['old_mode']
                require((live is None and expected_sha is None) or
                        (live is not None and _sha(live) == expected_sha and
                         stat.S_IMODE(paths.regular_file(str(path)).st_mode) == expected_mode),
                        'finished patch input changed: ' + row['name'])
            clean_stage(record)
            if complete:
                return
            return transaction(sdk, work, source, changes, old_cookie, new_inventory, build_clean, inject=inject)
        paths.real_directory(str(staging))
        require(stable_read(paths, staging / 'cookie-old') == old_cookie and
                stable_read(paths, staging / 'cookie-new') == new_cookie,
                'patch refresh journal identity changed')
    try:
        step('prepared')
        for index, row in enumerate(record['files']):
            require(isinstance(row, dict) and row.get('index') == index and
                    re.fullmatch(r'[0-9a-f]{64}', row.get('new_sha', '')) and
                    (row.get('old_sha') is None or re.fullmatch(r'[0-9a-f]{64}', row['old_sha'])),
                    'invalid patch refresh journal entry')
            path = _entry(paths, source, row['name'])
            live = read_or_none(path)
            live_mode = None if live is None else stat.S_IMODE(paths.regular_file(str(path)).st_mode)
            if live is not None and _sha(live) == row['new_sha'] and live_mode == row['new_mode']:
                continue
            require((live is None and row['old_sha'] is None) or
                    (live is not None and _sha(live) == row['old_sha'] and live_mode == row['old_mode']),
                    'live input changed during refresh: ' + row['name'])
            new = staging / ('new-' + str(index))
            require(_sha(stable_read(paths, new)) == row['new_sha'] and
                    stat.S_IMODE(paths.regular_file(str(new)).st_mode) == row['new_mode'],
                    'staged input changed')
            if live is None:
                os.link(new, path, follow_symlinks=False)
                new.unlink()
            else:
                os.replace(new, path)
            step('file-' + str(index))
        current_cookie = stable_read(paths, cookie)
        require(current_cookie in (old_cookie, new_cookie), 'patch cookie changed during refresh')
        require(record['phase'] != 'cookie' or current_cookie == new_cookie,
                'committed patch cookie changed')
        if current_cookie == old_cookie and record['phase'] != 'cookie':
            candidate = staging / 'cookie-next'
            cookie_mode = stat.S_IMODE(paths.regular_file(str(cookie)).st_mode)
            if os.path.lexists(candidate):
                require(stable_read(paths, candidate) == new_cookie and
                        stat.S_IMODE(paths.regular_file(str(candidate)).st_mode) == cookie_mode,
                        'staged patch cookie changed')
            else:
                _write_exclusive(candidate, new_cookie, cookie_mode)
            step('cookie-next')
            os.replace(candidate, cookie)
        record['phase'] = 'cookie'
        jsonio.write_json(str(marker), record, exclusive=False)
        step('cookie')
        build_clean()
        step('build-clean')
        record['phase'] = 'complete'
        jsonio.write_json(str(marker), record, exclusive=False)
        step('complete')
        clean_stage(record)
    except BaseException:
        # A replacement patch can keep the same inventory cookie. The journal
        # phase, rather than equal cookie bytes, records the commit in that case.
        # Once committed, retain it for an idempotent build-clean retry.
        if record['phase'] not in ('cookie', 'complete') and stable_read(paths, cookie) == old_cookie:
            rollback(record)
        raise


def validate_added_revision_includes(paths, recipe, names, selected_values, oldcmd, cmd):
    """Accept new literal revision metadata only when build inputs are unchanged."""
    variables = set()
    for name in sorted(names):
        data = stable_read(paths, recipe / name).decode('utf-8')
        count = 0
        for line in data.splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            match = re.fullmatch(r' *([A-Z][A-Z0-9_]*_REVISION) *= *([0-9]+)[ \t]*(?:#.*)?', line)
            require(match is not None, 'invalid revision-only include: ' + name)
            variable = match.group(1)
            require(variable not in variables, 'duplicate variable in revision-only include: ' + variable)
            variables.add(variable)
            count += 1
        require(count, 'empty revision-only include: ' + name)
    # A revision variable can feed compiler flags or a recipe command. Its
    # spelling alone does not establish that it only changes package metadata.
    fields = ('OPSYS OS_VERSION MACHINE_ARCH MACHINE_GNU_PLATFORM ABI USE_CROSS_COMPILE '
              'PKG_OPTIONS PKGSRC_COMPILER EMBERBSD_CROSS_COMPILER_FAMILY EMBERBSD_HOST_COMPILER_FAMILY '
              'CC CXX CPP FC F77 AR AS LD NM RANLIB STRIP CFLAGS CXXFLAGS CPPFLAGS FFLAGS LDFLAGS '
              'CWRAPPERS_APPEND.cc CWRAPPERS_APPEND.cxx '
              'CONFIGURE_ARGS CONFIGURE_ENV CMAKE_CONFIGURE_ARGS MESON_ARGS '
              'MAKE_ENV MAKE_FLAGS BUILD_MAKE_FLAGS CMAKE_BUILD_ARGS BUILD_TARGET BUILD_DIRS '
              'CONFIGURE_DIR CONFIGURE_SCRIPT HAS_CONFIGURE GNU_CONFIGURE NO_CONFIGURE NO_BUILD '
              'USE_LANGUAGES USE_TOOLS TOOL_DEPENDS BUILD_DEPENDS DEPENDS '
              'PREFIX LOCALBASE TOOLBASE CROSS_DESTDIR TOOLDIR '
              'EMBERBSD_HOST_PREFIX EMBERBSD_CROSS_HOST_PREFIX EMBERBSD_CROSS_SYSROOT '
              'CMAKE CMAKE_GENERATOR CMAKE_BUILD_DIR _CMAKE_BUILD_SYSTEM _CMAKE_BUILD_TOOL '
              'GMAKE MAKE_PROGRAM PYTHONBIN TOOL_PYTHONBIN').split()
    before, after = selected_values(oldcmd, fields), selected_values(cmd, fields)
    changed = [name for name, old, new in zip(fields, before, after) if old != new]
    require(not changed, 'revision include changes build inputs: ' + ', '.join(changed))
    import subprocess
    hooks = ['-n', 'pre-configure', 'do-configure', 'post-configure',
             'pre-build', 'do-build', 'post-build']
    previous = subprocess.run(oldcmd + hooks, check=True, stdout=subprocess.PIPE).stdout
    current = subprocess.run(cmd + hooks, check=True, stdout=subprocess.PIPE).stdout
    require(previous == current, 'revision include changes configure/build commands')


def validate_recipe_includes(paths, recipe, makefiles, records, *, package=None, cwd=None, observed=None):
    """Bind old local includes to provenance and observe current recipe inputs."""
    import shlex
    root = Path(recipe).resolve(strict=True)
    base = Path(cwd).resolve(strict=True) if cwd is not None else root
    package = package or '/'.join(root.parts[-2:])
    result = set()
    for item in shlex.split(makefiles):
        path = Path(item)
        if not path.is_absolute():
            path = base / path
        path = path.resolve(strict=True)
        if path.is_relative_to(root) and path != root / 'Makefile':
            name = str(path.relative_to(root))
            require(not name.startswith('patches/') and name != 'distinfo',
                    'unsupported recipe-local makefile')
            data = stable_read(paths, path)
            if records is not None:
                expected = records.get(package + '/' + name)
                require(expected and _sha(data) == expected,
                        'included recipe input differs from installed provenance: ' + name)
            if observed is not None:
                require(path not in observed or observed[path] == data,
                        'included recipe input changed during verification: ' + name)
                observed[path] = data
            result.add(name)
    return result


def validate_timestamp_hooks(output, source, touch, find):
    """Accept only unchanged, bounded timestamp-copy hooks inside WRKSRC."""
    import shlex
    source = Path(source).resolve(strict=True)
    referenced, patterns = set(), set()
    def inside(value):
        path = Path(value)
        require(path.is_absolute() and path.is_relative_to(source) and
                path.resolve(strict=True).is_relative_to(source), 'patch hook path escapes source')
        relative = path.relative_to(source)
        require(relative.parts and all(x not in ('', '.', '..') for x in relative.parts),
                'invalid patch hook path')
        return str(relative)
    for line in output.splitlines():
        args = shlex.split(line)
        if args and args[0] == touch:
            require(len(args) >= 4 and args[1] == '-r', 'unsupported patch touch hook')
            referenced.add(inside(args[2]))
            referenced.update(inside(item) for item in args[3:])
        elif args and args[0] == find:
            require(len(args) == 10 and args[1] == str(source) and args[2] == '-name' and
                    re.fullmatch(r'[A-Za-z0-9_.+-]+', args[3]) and args[4] == '-exec' and
                    args[5] == touch and args[6] == '-r' and args[8:] == ['{}', '+'],
                    'unsupported patch find hook')
            referenced.add(inside(args[7])); patterns.add(args[3])
        else:
            raise ValueError('unsupported patch hook command')
    return referenced, patterns


def main():
    import argparse
    import shlex
    import subprocess
    import sys
    import tempfile
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk-source', type=Path, required=True)
    p.add_argument('--bmake', type=Path, required=True)
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--native', action='store_true')
    p.add_argument('--expected-work', type=Path, required=True)
    p.add_argument('--make-arg', action='append', default=[])
    p.add_argument('--previous-makefile', type=Path, help='installed package Makefile preimage')
    p.add_argument('--subst-class', help='one added pre-configure SUBST class')
    p.add_argument('--previous-recipe', type=Path, help='installed recipe preimage directory')
    p.add_argument('--refresh-subst', help='one existing substitution before configure')
    a = p.parse_args()
    sys.path.insert(0, str(a.sdk_source / 'src'))
    from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep
    require(archive_metadata.ARCHIVE_METADATA_API == 1 and sourceprep.SOURCE_PREPARATION_API == 2,
            'incompatible selected SDK')
    sdk = dict(paths=paths, jsonio=jsonio, archive_metadata=archive_metadata, sourceprep=sourceprep)
    names = ['WRKDIR', 'WRKSRC', 'PATCH', 'PATCH_ARGS', 'DISTDIR', 'DIST_SUBDIR', 'DISTFILES',
             'DISTNAME', 'PKG_DBDIR', 'CROSS_DESTDIR', 'PKGBASE', 'PKGVERSION_NOREV', 'PATCHFILES',
             'PATCHDIR', 'DISTINFO_FILE', 'EXTRACT_ONLY', 'LOCALPATCHES', 'META_PACKAGE', 'SUBST_CLASSES', '.MAKE.MAKEFILES']
    cmd = [str(a.bmake), '-C', str(a.recipe), '_MAKEVARS_MK=defined']
    if a.native:
        cmd.append('USE_CROSS_COMPILE=no')
    cmd.extend(a.make_arg)
    require(not a.refresh_subst or (a.previous_recipe and not a.previous_makefile and not a.subst_class),
            'existing substitution refresh requires previous recipe only')
    if a.refresh_subst:
        require(re.fullmatch(r'[A-Za-z0-9_-]+', a.refresh_subst), 'invalid SUBST class')
    require(not (a.previous_recipe and (a.previous_makefile or a.subst_class)),
            'previous recipe and added substitution modes are exclusive')
    require(bool(a.previous_makefile) == bool(a.subst_class),
            'configure-aware refresh needs previous Makefile and SUBST class')
    if a.subst_class:
        require(re.fullmatch(r'[A-Za-z0-9_-]+', a.subst_class), 'invalid SUBST class')
        require(a.previous_makefile.is_absolute(), 'previous Makefile must be absolute')
    hooks = subprocess.run(cmd + ['-n', 'pre-patch', 'post-patch'], check=True,
                           stdout=subprocess.PIPE, text=True)
    if not a.subst_class:
        require(not hooks.stdout.strip(), 'custom patch hooks are unsupported')
    result = subprocess.run(cmd + ['show-vars', 'VARNAMES=' + ' '.join(names)],
                            check=True, stdout=subprocess.PIPE, text=True)
    values = result.stdout.splitlines()
    require(len(values) == len(names), 'unexpected selected bmake metadata')
    v = dict(zip(names, values))
    require(not v['PATCHFILES'], 'downloaded patchfiles are unsupported')
    require(Path(v['PATCHDIR']).resolve() == (a.recipe / 'patches').resolve() and
            Path(v['DISTINFO_FILE']).resolve() == (a.recipe / 'distinfo').resolve(),
            'nonstandard patch inventory is unsupported')
    require(not v['META_PACKAGE'], 'meta packages are unsupported')
    if v['LOCALPATCHES']:
        require(not (Path(v['LOCALPATCHES']) / '/'.join(a.recipe.parts[-2:])).exists(),
                'additional local patches are unsupported')
    framework_files = {(a.recipe.parents[1] / name).resolve() for name in
                       ('mk/patch/patch.mk', 'mk/bsd.prefs.mk')}
    validate_active_target(paths, cmd, a.recipe, v['.MAKE.MAKEFILES'], framework_files, 'do-patch')
    distfiles = shlex.split(v['DISTFILES'])
    require(len(distfiles) == 1 and '/' not in distfiles[0], 'unsupported archive inventory')
    require(shlex.split(v['EXTRACT_ONLY']) == distfiles, 'custom archive selection is unsupported')
    work = Path(v['WRKDIR']); source = Path(v['WRKSRC'])
    require(paths.canonical_existing(str(work)) == paths.canonical_existing(str(a.expected_work)),
            'selected WRKDIR differs from locked stage')
    require(source.name == v['DISTNAME'] and source.parent == work, 'unsupported archive layout')
    patch_args = shlex.split(v['PATCH_ARGS'])
    require(patch_args[:2] == ['-d', str(source)], 'unexpected patch destination')
    dbdir = Path(v['PKG_DBDIR'])
    if not a.native:
        dbdir = Path(v['CROSS_DESTDIR']) / str(dbdir).lstrip('/')
    candidates = list(dbdir.glob(v['PKGBASE'] + '-' + v['PKGVERSION_NOREV'] + '*'))
    candidates = [x for x in candidates if x.is_dir() and re.fullmatch(re.escape(v['PKGBASE'] + '-' + v['PKGVERSION_NOREV']) + r'(?:nb[0-9]+)?', x.name)]
    require(len(candidates) == 1, 'expected exactly one compatible installed package owner')
    owner = candidates[0] / '+BUILD_VERSION'
    if a.subst_class:
        records = {}
        for line in stable_read(paths, owner).decode('utf-8').splitlines():
            if ': ' in line:
                key, value = line.rsplit(': ', 1)
                key = os.path.normpath(key)
                require(key not in records, 'duplicate installed source record')
                records[key] = value
        key = '/'.join(a.recipe.parts[-2:]) + '/Makefile'
        previous_data = stable_read(paths, a.previous_makefile)
        require(records.get(key) == _sha(previous_data),
                'previous Makefile differs from installed provenance')
        oldcmd = cmd[:3] + ['-f', str(a.previous_makefile)] + cmd[3:]
        old_hooks = subprocess.run(oldcmd + ['-n', 'pre-patch', 'post-patch'], check=True,
                                   stdout=subprocess.PIPE, text=True)
        require(hooks.stdout == old_hooks.stdout, 'patch hooks changed since installed package')
        old_meta = subprocess.run(oldcmd + ['show-vars', 'VARNAMES=SUBST_CLASSES .MAKE.MAKEFILES'],
                                  check=True, stdout=subprocess.PIPE, text=True).stdout.splitlines()
        require(len(old_meta) == 2, 'unexpected previous recipe metadata')
        validate_active_target(paths, oldcmd, a.recipe, old_meta[1], framework_files, 'do-patch')
        old_subst = old_meta[0].split()
        old_includes = validate_recipe_includes(paths, a.recipe, old_meta[1], records)
        current_includes = validate_recipe_includes(paths, a.recipe, v['.MAKE.MAKEFILES'], records)
        require(old_includes == current_includes, 'included recipe inputs changed')
        require(stable_read(paths, a.previous_makefile) == previous_data, 'previous Makefile changed during verification')
        current_subst = v['SUBST_CLASSES'].split()
        require(len(current_subst) == len(set(current_subst)) and a.subst_class not in old_subst and
                set(current_subst) == set(old_subst) | {a.subst_class},
                'unsupported SUBST class transition')
        attributes = ['SUBST_STAGE.', 'SUBST_FILES.', 'SUBST_VARS.', 'SUBST_SED.',
                      'SUBST_NOOP_OK.', '_SUBST_COOKIE.']
        fields = [x + a.subst_class for x in attributes] + ['PKG_FAIL_REASON']
        selected = subprocess.run(cmd + ['show-vars', 'VARNAMES=' + ' '.join(fields)],
                                  check=True, stdout=subprocess.PIPE, text=True).stdout.splitlines()
        require(len(selected) == len(fields), 'unexpected SUBST metadata')
        stage, files, variables, sed, noop, subst_cookie, failed = selected
        subst_files = shlex.split(files)
        require(stage == 'pre-configure' and subst_files and len(set(subst_files)) == len(subst_files) and
                all(re.fullmatch(r'[A-Za-z0-9_./+-]+', name) and
                    not name.startswith('/') and all(part not in ('', '.', '..') for part in name.split('/'))
                    for name in subst_files), 'unsupported SUBST files or stage')
        require(variables.split() and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', item)
                                         for item in variables.split()) and not sed and
                noop.lower() == 'no' and not failed, 'unsupported SUBST transformation')
        require(Path(subst_cookie) == work / ('.subst_' + a.subst_class + '_done'),
                'unexpected SUBST cookie')
        tool_values = subprocess.run(cmd + ['show-vars', 'VARNAMES=TOUCH FIND'], check=True,
                                     stdout=subprocess.PIPE, text=True).stdout.splitlines()
        require(len(tool_values) == 2 and all(Path(item).is_absolute() for item in tool_values),
                'invalid selected patch hook tools')
        hook_files, hook_patterns = validate_timestamp_hooks(hooks.stdout, source, *tool_values)
        if not (work / '.emberbsd-patch-refresh.json').exists():
            require(not os.path.lexists(subst_cookie), 'new SUBST class is already recorded')
        elif os.path.lexists(subst_cookie):
            require(stable_read(paths, Path(subst_cookie)) == b'', 'foreign SUBST cookie during retry')
        pending_cookie = Path(subst_cookie + '.tmp')
        if os.path.lexists(pending_cookie):
            require(stable_read(paths, pending_cookie) == b'', 'foreign pending SUBST cookie')
    if a.previous_recipe:
        package = '/'.join(a.recipe.parts[-2:])
        previous_makefile = a.previous_recipe / 'Makefile'
        observed_recipe_inputs = {a.recipe / 'Makefile': stable_read(paths, a.recipe / 'Makefile')}
        records = {}
        for line in stable_read(paths, owner).decode('utf-8').splitlines():
            if ': ' in line:
                key, value = line.rsplit(': ', 1)
                key = os.path.normpath(key)
                require(key not in records, 'duplicate installed source record')
                records[key] = value
        previous_data = stable_read(paths, previous_makefile)
        require(records.get(package + '/Makefile') == _sha(previous_data),
                'previous Makefile differs from installed provenance')
        observed_recipe_inputs[previous_makefile] = previous_data
        oldcmd = cmd[:3] + ['-f', str(previous_makefile)] + cmd[3:]
        old_hooks = subprocess.run(oldcmd + ['-n', 'pre-patch', 'post-patch'], check=True,
                                   stdout=subprocess.PIPE, text=True)
        require(not hooks.stdout.strip() and old_hooks.stdout == hooks.stdout,
                'custom or changed patch hooks are unsupported')
        def selected_values(command, fields):
            result = subprocess.run(command + ['show-vars', 'VARNAMES=' + ' '.join(fields)],
                                    check=True, stdout=subprocess.PIPE, text=True).stdout.splitlines()
            require(len(result) == len(fields), 'unexpected previous recipe metadata')
            return result
        old_classes, old_makefiles = selected_values(oldcmd, ['SUBST_CLASSES', '.MAKE.MAKEFILES'])
        validate_active_target(paths, oldcmd, a.recipe, old_makefiles, framework_files, 'do-patch',
                               previous_recipe=a.previous_recipe, observed=observed_recipe_inputs)
        require(old_classes == v['SUBST_CLASSES'], 'previous SUBST classes changed')
        old_includes = validate_recipe_includes(paths, a.previous_recipe, old_makefiles, records,
                                               package=package, cwd=a.recipe, observed=observed_recipe_inputs)
        old_includes |= validate_recipe_includes(paths, a.recipe, old_makefiles, records,
                                                observed=observed_recipe_inputs)
        new_includes = validate_recipe_includes(paths, a.recipe, v['.MAKE.MAKEFILES'], None,
                                               observed=observed_recipe_inputs)
        require(old_includes <= new_includes, 'included recipe inputs removed')
        if new_includes != old_includes:
            validate_added_revision_includes(paths, a.recipe, new_includes - old_includes,
                                             selected_values, oldcmd, cmd)
        # Configuration and package policy may legitimately change in a local
        # include. The complete old recipe still supplies source preimages;
        # require unchanged source preparation and replay the current configure.
        source_fields = ['WRKDIR', 'WRKSRC', 'DISTDIR', 'DIST_SUBDIR', 'DISTNAME',
                         'DISTFILES', 'EXTRACT_ONLY', 'EXTRACT_USING', 'EXTRACT_SUFX',
                         'EXTRACT_CMD', 'EXTRACT_ENV', 'EXTRACT_BEFORE_ARGS', 'EXTRACT_AFTER_ARGS',
                         'PATCH', 'PATCH_ARGS', 'PATCHFILES', 'PATCHDIR', 'DISTINFO_FILE', 'LOCALPATCHES']
        old_source, new_source = selected_values(oldcmd, source_fields), selected_values(cmd, source_fields)
        require(old_source == new_source, 'previous source preparation inputs changed')
        require(all(name not in v or value == v[name] for name, value in zip(source_fields, new_source)),
                'current source preparation inputs changed during verification')
        for command in (oldcmd, cmd):
            result = subprocess.run(command + ['-n', 'pre-extract', 'post-extract'], check=True,
                                    stdout=subprocess.PIPE, text=True).stdout
            if command is oldcmd:
                old_extract_hooks = result
            else:
                require(result == old_extract_hooks, 'previous extraction hooks changed')
        extract_framework = (a.recipe.parents[1] / 'mk/extract/extract.mk').resolve()
        validate_active_target(paths, oldcmd, a.recipe, old_makefiles, {extract_framework}, 'do-extract',
                               previous_recipe=a.previous_recipe, observed=observed_recipe_inputs)
        validate_active_target(paths, cmd, a.recipe, v['.MAKE.MAKEFILES'], {extract_framework}, 'do-extract')
        class_names = old_classes.split()
        require(len(class_names) == len(set(class_names)) and
                all(re.fullmatch(r'[A-Za-z0-9_.-]+', name) for name in class_names),
                'unsupported previous SUBST classes')
        attributes = ('SUBST_STAGE.', 'SUBST_FILES.', 'SUBST_VARS.', 'SUBST_SED.',
                      'SUBST_FILTER_CMD.', 'SUBST_SKIP_TEXT_CHECK.', 'SUBST_NOOP_OK.', '_SUBST_COOKIE.')
        fields = ['PKG_FAIL_REASON'] + [attribute + name for name in class_names for attribute in attributes]
        before, after = selected_values(oldcmd, fields), selected_values(cmd, fields)
        require(before[0] == after[0] and not before[0], 'previous recipe reports a failure')
        subst_metadata = {}
        for index, name in enumerate(class_names):
            start = 1 + index * len(attributes)
            old_values = tuple(before[start:start + len(attributes)])
            new_values = tuple(after[start:start + len(attributes)])
            require(old_values == new_values, 'previous SUBST configuration changed: ' + name)
            subst_metadata[name] = new_values
        require(stable_read(paths, previous_makefile) == previous_data,
                'previous Makefile changed during verification')
    if a.refresh_subst:
        require(a.refresh_subst in subst_metadata,
                'existing SUBST class not uniquely present')
        stage, files, variables, sed, filter_cmd, skip, noop, subst_cookie = subst_metadata[a.refresh_subst]
        subst_files = shlex.split(files)
        require(stage in ('pre-configure', 'do-configure-pre-hook') and subst_files and
                len(set(subst_files)) == len(subst_files) and
                all(re.fullmatch(r'[A-Za-z0-9_./+-]+', name) and not name.startswith('/') and
                    all(part not in ('', '.', '..') for part in name.split('/')) for name in subst_files),
                'unsupported existing SUBST files or stage')
        require(filter_cmd and (sed or variables), 'unsupported existing SUBST transformation')
        require(Path(subst_cookie) == work / ('.subst_' + a.refresh_subst + '_done'),
                'unexpected existing SUBST cookie')
        live_subst_cookie = stable_read(paths, Path(subst_cookie))
        require(not os.path.lexists(subst_cookie + '.tmp'), 'unexpected pending existing SUBST cookie')
        subst_candidates = {}
    archive = Path(v['DISTDIR']) / v['DIST_SUBDIR'] / distfiles[0]
    marker = work / '.emberbsd-patch-refresh.json'
    old_cookie = journal_old_cookie(sdk, work) if marker.exists() else None
    with tempfile.TemporaryDirectory(prefix='.patch-refresh-candidates-', dir=work) as scratch:
        def transform(candidate, affected):
            require(set(subst_files) == affected, 'SUBST files must exactly match added patch targets')
            require(not (hook_files & affected) and not any(Path(name).name in hook_patterns for name in affected),
                    'changed patch target participates in a timestamp hook')
            scratch_cookie = Path(scratch) / 'subst-candidate-cookie'
            subprocess.run(cmd + ['WRKSRC=' + str(candidate),
                                  '_SUBST_COOKIE.' + a.subst_class + '=' + str(scratch_cookie),
                                  'subst-' + a.subst_class], check=True)
            require(scratch_cookie.is_file(), 'pkgsrc SUBST did not create its cookie')
        def existing_transform(label, command, candidate, affected):
            for name in subst_files:
                path = _entry(paths, candidate, name)
                paths.regular_file(str(path))
                require(not os.path.lexists(str(path) + '.subst.sav'),
                        'unexpected existing SUBST temporary file')
            scratch_cookie = Path(scratch) / ('existing-subst-' + label)
            subprocess.run(command + ['WRKSRC=' + str(candidate),
                                      '_SUBST_COOKIE.' + a.refresh_subst + '=' + str(scratch_cookie),
                                      'subst-' + a.refresh_subst], check=True)
            require(stable_read(paths, scratch_cookie) == live_subst_cookie,
                    'existing SUBST cookie differs from replay')
            subst_candidates[label] = {name: stable_read(paths, _entry(paths, candidate, name))
                                       for name in subst_files}
            require(all(not os.path.lexists(str(_entry(paths, candidate, name)) + '.subst.sav')
                        for name in subst_files), 'existing SUBST temporary file remains')
        changes, cookie, inventory = prepare(sdk, a.recipe, work, archive, v['DISTNAME'], owner,
                                             Path(v['PATCH']), patch_args[2:], Path(scratch), old_cookie=old_cookie,
                                             transform=(transform if a.subst_class else
                                                        (lambda candidate, affected: existing_transform('new', cmd, candidate, affected))
                                                        if a.refresh_subst else None),
                                             old_transform=(lambda candidate, affected: existing_transform('old', oldcmd, candidate, affected))
                                                           if a.refresh_subst else None,
                                             allow_completed=bool(a.subst_class),
                                             previous_recipe=a.previous_recipe)
        if a.refresh_subst:
            for name in subst_files:
                if subst_candidates['old'][name] == subst_candidates['new'][name]:
                    require(stable_read(paths, _entry(paths, source, name)) == subst_candidates['old'][name],
                            'unchanged existing SUBST input differs: ' + name)
        classes = [name for name in shlex.split(v['SUBST_CLASSES'])
                   if name not in (a.subst_class, a.refresh_subst)]
        if classes:
            require(all(re.fullmatch(r'[A-Za-z0-9_.-]+', name) for name in classes),
                    'unsupported substitution class')
            requested = ['SUBST_FILES.' + name for name in classes]
            values = subprocess.run(cmd + ['show-vars', 'VARNAMES=' + ' '.join(requested)],
                                    check=True, stdout=subprocess.PIPE, text=True).stdout.splitlines()
            require(len(values) == len(requested), 'unexpected substitution metadata')
            changed = {row[0] for row in changes}
            for value in values:
                files = shlex.split(value)
                require(files, 'unsupported substitution paths')
                for name in files:
                    if '*' in name or '?' in name:
                        candidates = [Path(scratch) / label / v['DISTNAME'] for label in ('old', 'new')]
                        unselected_subst_pattern(paths, [*candidates, source], name, changed)
                        continue
                    require(re.fullmatch(r'[A-Za-z0-9_+./-]+', name) and
                            not name.startswith('/') and
                            all(part not in ('', '.', '..') for part in name.split('/')),
                            'unsupported substitution paths')
                    require(name not in changed, 'changed source needs substitution refresh')
                    if not unselected_subst_file(paths, source, name):
                        for label in ('old', 'new'):
                            candidate = Path(scratch) / label / v['DISTNAME']
                            require(not unselected_subst_file(paths, candidate, name),
                                    'missing substitution input differs from archive: ' + name)
        def clean():
            if a.previous_recipe:
                for path, contents in observed_recipe_inputs.items():
                    require(stable_read(paths, path) == contents,
                            'recipe input changed before configure invalidation: ' + str(path))
            subprocess.run(cmd + ['configure-clean' if (a.subst_class or a.previous_recipe) else 'build-clean'], check=True)
            if a.refresh_subst:
                require(stable_read(paths, Path(subst_cookie)) == live_subst_cookie,
                        'existing SUBST cookie changed')
                for name in subst_files:
                    require(stable_read(paths, _entry(paths, source, name)) == subst_candidates['new'][name],
                            'existing SUBST result differs: ' + name)
            if a.subst_class:
                # Every target is byte-verified against the pkgsrc-transformed
                # candidate before permitting this one no-op SUBST invocation.
                for name, _before, after, _old_mode, _new_mode in changes:
                    require(stable_read(paths, source / name) == after,
                            'configured patch result changed before SUBST')
                subprocess.run(cmd + ['SUBST_NOOP_OK.' + a.subst_class + '=yes',
                                      'subst-' + a.subst_class], check=True)
                require(stable_read(paths, Path(subst_cookie)) == b'',
                        'pkgsrc SUBST did not record the expected no-op result')
        if a.previous_recipe:
            for path, contents in observed_recipe_inputs.items():
                require(stable_read(paths, path) == contents,
                        'recipe input changed during source replay: ' + str(path))
        transaction(sdk, work, source, changes, cookie,
                    [a.recipe / 'patches' / name for name in inventory], clean)
    print('Refreshed verified patch inputs; compatible build objects retained.')


if __name__ == '__main__':
    main()
