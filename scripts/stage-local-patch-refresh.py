#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify and prepare an additive pkgsrc stage patch refresh.

This module never accepts an unverified old patch list or a caller-supplied
replacement digest. The controlling owner holds the stage lock for its lifetime.
"""
import base64
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat


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


def old_metadata(paths, recipe, work, installed_version, old_cookie=None):
    """Bind the old ordered cookie to installed BUILD_VERSION and current recipe."""
    cookie = stable_read(paths, work / '.patch_done') if old_cookie is None else old_cookie
    try:
        old_paths = [Path(s) for s in cookie.decode('utf-8').splitlines() if s]
    except UnicodeError as exc:
        raise ValueError('invalid old patch cookie') from exc
    patchdir = (recipe / 'patches').resolve(strict=True)
    require(old_paths and all(p.is_absolute() and p.resolve(strict=True).parent == patchdir for p in old_paths),
            'old patch cookie contains an unsupported path')
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
    new = sorted(p.name for p in patchdir.glob('patch-*') if p.is_file())
    require([p for p in new if p in old] == old and len(new) > len(old),
            'old patch list is not a proper subsequence')
    for name in old:
        expected = records.get(pkgpath + '/patches/' + name)
        require(expected and hashlib.sha256(stable_read(paths, patchdir / name)).hexdigest() == expected,
                'old patch identity changed: ' + name)
    additions = [p for p in new if p not in old]
    distinfo = stable_read(paths, recipe / 'distinfo')
    old_distinfo = b''.join(line for line in distinfo.splitlines(keepends=True)
                            if not any(line.startswith(b'SHA1 (' + name.encode() + b') = ') for name in additions))
    expected = records.get(pkgpath + '/distinfo')
    require(expected and hashlib.sha256(old_distinfo).hexdigest() == expected,
            'old distinfo cannot be reconstructed exactly')
    return old, new, additions, cookie


def prepare(sdk, recipe, work, archive, archive_root, installed_version, patch, patch_args, scratch, *, old_cookie=None):
    """Replay complete old and current patch order and return validated leaf changes."""
    paths, sourceprep, archive_metadata = sdk['paths'], sdk['sourceprep'], sdk['archive_metadata']
    recipe, work, archive, scratch = map(Path, (recipe, work, archive, scratch))
    old, new, additions, old_cookie = old_metadata(paths, recipe, work, installed_version, old_cookie)
    metadata, patches = archive_metadata.read_recipe(recipe, archive.name, archive_root)
    data = stable_read(paths, archive)
    measured = sourceprep.archive_hashes(data)
    require(all(measured[k] == metadata[k] for k in ('sha512', 'blake2s', 'size')),
            'archive differs from verified distinfo')
    require([p.name for p in patches] == new, 'current patch inventory changed')
    require(patch_args == ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'],
            'unsupported selected pkgsrc PATCH_ARGS')
    affected = set()
    for name in additions:
        affected.update(targets(stable_read(paths, recipe / 'patches' / name)))
    candidates = []
    for label, series in (('old', old), ('new', new)):
        dest = scratch / label
        dest.mkdir()
        sourceprep.extract_archive(archive, dest, archive_root, label)
        tree = dest / archive_root
        for name in series:
            path = recipe / 'patches' / name
            contents = stable_read(paths, path)
            require(hashlib.sha256(contents).hexdigest() == metadata['recipe']['patches/' + name],
                    'patch changed during replay: ' + name)
            sourceprep.apply_patch(str(patch), path, contents, tree, label,
                                   patch_args=tuple(patch_args), allow_dev_null=True)
            require(stable_read(paths, path) == contents, 'patch changed while applying: ' + name)
        candidates.append(tree)
    require(sourceprep.archive_hashes(stable_read(paths, archive)) == measured,
            'archive changed during replay')
    changes = []
    for name in sorted(affected):
        before, after = (tree / name for tree in candidates)
        require(not before.is_symlink() and not after.is_symlink(), 'symlink patch target')
        old_data = stable_read(paths, before) if before.is_file() else None
        new_data = stable_read(paths, after) if after.is_file() else None
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
        if old_data != new_data or old_mode != new_mode:
            changes.append((name, old_data, new_data, old_mode, new_mode))
    require(changes, 'additive patch series has no source changes')
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
        if current_cookie == old_cookie:
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
        # Once the cookie is updated, retain the journal for build-clean retry.
        if stable_read(paths, cookie) == old_cookie:
            rollback(record)
        raise


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
    hooks = subprocess.run(cmd + ['-n', 'pre-patch', 'post-patch'], check=True,
                           stdout=subprocess.PIPE, text=True)
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
    for item in shlex.split(v['.MAKE.MAKEFILES']):
        makefile = Path(item)
        if not makefile.is_absolute():
            makefile = a.recipe / makefile
        if re.search(rb'(?m)^\s*do-patch\s*:', stable_read(paths, makefile)):
            require(makefile.resolve() in framework_files, 'custom do-patch is unsupported')
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
    archive = Path(v['DISTDIR']) / v['DIST_SUBDIR'] / distfiles[0]
    marker = work / '.emberbsd-patch-refresh.json'
    old_cookie = journal_old_cookie(sdk, work) if marker.exists() else None
    with tempfile.TemporaryDirectory(prefix='.patch-refresh-candidates-', dir=work) as scratch:
        changes, cookie, inventory = prepare(sdk, a.recipe, work, archive, v['DISTNAME'], owner,
                                             Path(v['PATCH']), patch_args[2:], Path(scratch), old_cookie=old_cookie)
        classes = shlex.split(v['SUBST_CLASSES'])
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
                require(files and all(re.fullmatch(r'[A-Za-z0-9_+./-]+', name) and
                        not name.startswith('/') and all(part not in ('', '.', '..') for part in name.split('/'))
                        for name in files), 'unsupported substitution paths')
                for name in files:
                    current = source
                    for part in name.split('/')[:-1]:
                        current = current / part
                        paths.real_directory(str(current))
                    paths.regular_file(str(current / name.split('/')[-1]))
                require(not changed.intersection(files), 'changed source needs substitution refresh')
        transaction(sdk, work, source, changes, cookie,
                    [a.recipe / 'patches' / name for name in inventory],
                    lambda: subprocess.run(cmd + ['build-clean'], check=True))
    print('Refreshed verified patch inputs; compatible build objects retained.')


if __name__ == '__main__':
    main()
