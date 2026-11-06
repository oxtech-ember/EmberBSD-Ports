#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Refresh an explicit set of prepared pkgsrc source leaves in a retained stage.

The selected bmake prepares a fresh sibling WRKDIR with the package's actual
extract and patch targets. Only caller-authorized regular files may differ;
all other candidate WRKSRC inputs must match the retained source tree.
"""
import base64
import importlib.util
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile


def require(ok, message):
    if not ok:
        raise ValueError(message)


def source_refresh(sdk, patch_refresh, bmake, recipe, work, make_args, scope):
    paths = sdk['paths']
    base = [str(bmake), '-C', str(recipe), '_MAKEVARS_MK=defined', *make_args]

    def variables(wrkdir):
        args = base + ['WRKDIR=' + str(wrkdir), 'show-vars',
                       'VARNAMES=WRKDIR WRKSRC']
        values = subprocess.run(args, check=True, stdout=subprocess.PIPE,
                                text=True).stdout.splitlines()
        require(len(values) == 2, 'unexpected selected bmake source metadata')
        result = dict(zip(('WRKDIR', 'WRKSRC'), values))
        require(Path(result['WRKDIR']).resolve() == wrkdir.resolve(),
                'selected candidate WRKDIR differs')
        src = Path(result['WRKSRC']).resolve()
        require(src.is_absolute() and src.is_relative_to(wrkdir.resolve()),
                'selected WRKSRC is outside candidate WRKDIR')
        return src

    selected_work = Path(subprocess.run(base + ['show-var', 'VARNAME=WRKDIR'],
                                        check=True, stdout=subprocess.PIPE,
                                        text=True).stdout.strip())
    require(paths.canonical_existing(str(selected_work)) == paths.canonical_existing(str(work)),
            'selected WRKDIR differs from locked stage')
    work = Path(paths.canonical_existing(str(work)))
    retained_source = Path(subprocess.run(base + ['show-var', 'VARNAME=WRKSRC'],
                                          check=True, stdout=subprocess.PIPE,
                                          text=True).stdout.strip()).resolve()
    paths.real_directory(str(work))
    paths.real_directory(str(retained_source))
    require(retained_source.is_relative_to(work), 'retained WRKSRC is outside locked stage')
    retained_rel_source = retained_source.relative_to(work)

    require(scope and len(scope) == len(set(scope)), 'empty or duplicate source refresh scope')
    for name in scope:
        rel = PurePosixPath(name)
        require(not rel.is_absolute() and all(part not in ('', '.', '..') for part in name.split('/')) and
                str(rel) == name,
                'invalid source refresh path: ' + name)

    # Candidate WRKDIR is a unique sibling so it uses the same filesystem while
    # remaining outside the retained package tree.
    with tempfile.TemporaryDirectory(prefix='.source-refresh-', dir=work.parent) as tmp:
        candidate_work = Path(tmp) / 'work'
        candidate_work.mkdir()
        candidate_source = variables(candidate_work)
        subprocess.run(base + ['WRKDIR=' + str(candidate_work), 'extract', 'patch'], check=True)
        candidate_source = variables(candidate_work)
        paths.real_directory(str(candidate_source))
        rel_source = candidate_source.relative_to(candidate_work.resolve())
        require(rel_source == retained_rel_source,
                'candidate WRKSRC relative path differs from retained stage')
        retained_source = work / retained_rel_source
        paths.real_directory(str(retained_source))
        candidate_cookie = candidate_work / '.patch_done'
        paths.regular_file(str(candidate_cookie))
        new_cookie = patch_refresh.stable_read(paths, candidate_cookie)
        old_cookie = patch_refresh.stable_read(paths, work / '.patch_done')
        journal_path = work / '.emberbsd-patch-refresh.json'
        if journal_path.exists():
            journal = sdk['jsonio'].read_json(str(journal_path))
            try:
                journal_cookie = base64.b64decode(journal['old_cookie_b64'], validate=True)
            except (KeyError, ValueError) as exc:
                raise ValueError('invalid source refresh journal cookie') from exc
            old_cookie = journal_cookie

        changes = []
        candidate_names = set()
        for root, dirs, files in os.walk(candidate_source, followlinks=False):
            kept_dirs = []
            for dirname in sorted(dirs):
                candidate_dir = Path(root) / dirname
                rel_dir = candidate_dir.relative_to(candidate_source).as_posix()
                live_dir = retained_source / rel_dir
                if candidate_dir.is_symlink():
                    require(live_dir.is_symlink() and os.readlink(candidate_dir) == os.readlink(live_dir),
                            'unexpected source symlink difference: ' + rel_dir)
                else:
                    kept_dirs.append(dirname)
            dirs[:] = kept_dirs
            for basename in sorted(files):
                candidate = Path(root) / basename
                rel = candidate.relative_to(candidate_source).as_posix()
                if rel.endswith('.orig'):
                    continue
                candidate_names.add(rel)
                live = retained_source / rel
                if candidate.is_symlink():
                    require(rel not in scope, 'authorized source leaf is not a regular file: ' + rel)
                    require(live.is_symlink() and os.readlink(candidate) == os.readlink(live),
                            'unexpected source symlink difference: ' + rel)
                    continue
                paths.regular_file(str(candidate))
                if rel in scope:
                    require(not live.is_symlink(), 'authorized source leaf is not a regular file: ' + rel)
                    paths.regular_file(str(live))
                    before = patch_refresh.stable_read(paths, live)
                    after = patch_refresh.stable_read(paths, candidate)
                    old_mode = stat.S_IMODE(paths.regular_file(str(live)).st_mode)
                    new_mode = stat.S_IMODE(paths.regular_file(str(candidate)).st_mode)
                    if before != after or old_mode != new_mode:
                        changes.append((rel, before, after, old_mode, new_mode))
                else:
                    require(not live.is_symlink(), 'source file became a symlink: ' + rel)
                    live_stat = paths.regular_file(str(live))
                    require(patch_refresh.stable_read(paths, live) ==
                            patch_refresh.stable_read(paths, candidate),
                            'unexpected source difference outside explicit scope: ' + rel)
                    require(stat.S_IMODE(live_stat.st_mode) ==
                            stat.S_IMODE(paths.regular_file(str(candidate)).st_mode),
                            'unexpected source mode difference outside explicit scope: ' + rel)
        require(set(scope) <= candidate_names, 'authorized source leaf is absent from candidate WRKSRC')
        journal_expected = None
        if journal_path.exists():
            record = sdk['jsonio'].read_json(str(journal_path))
            staging = work / '.emberbsd-patch-refresh'
            resumed = []
            journal_names = set()
            for row in record.get('files', []):
                name, index = row.get('name'), row.get('index')
                require(name in scope and isinstance(index, int), 'source refresh journal scope changed')
                journal_names.add(name)
                candidate = candidate_source / name
                paths.regular_file(str(candidate))
                after = patch_refresh.stable_read(paths, candidate)
                new_mode = stat.S_IMODE(paths.regular_file(str(candidate)).st_mode)
                require(name in candidate_names and
                        patch_refresh._sha(after) == row.get('new_sha') and
                        new_mode == row.get('new_mode'),
                        'candidate no longer matches source refresh journal')
                if record.get('phase') in ('complete', 'rolled-back'):
                    before, old_mode = after, row.get('old_mode')
                    resumed.append((name, before, after, old_mode, new_mode))
                    continue
                if row.get('old_sha') is None:
                    before, old_mode = None, None
                else:
                    old = staging / ('old-' + str(index))
                    if os.path.lexists(old):
                        before = patch_refresh.stable_read(paths, old)
                        old_mode = stat.S_IMODE(paths.regular_file(str(old)).st_mode)
                    else:
                        require(record.get('phase') == 'preparing',
                                'source refresh journal preimage is missing')
                        live = retained_source / name
                        before = patch_refresh.stable_read(paths, live)
                        old_mode = stat.S_IMODE(paths.regular_file(str(live)).st_mode)
                require(patch_refresh._sha(after) == row.get('new_sha') and
                        ((patch_refresh._sha(before) == row.get('old_sha')) if before is not None
                         else row.get('old_sha') is None) and
                        new_mode == row.get('new_mode') and old_mode == row.get('old_mode'),
                        'candidate no longer matches source refresh journal')
                resumed.append((name, before, after, old_mode, new_mode))
            require(resumed, 'authorized source leaves are already current')
            fresh_names = {row[0] for row in changes}
            require(fresh_names <= journal_names,
                    'candidate has new authorized source changes outside the pending journal: ' +
                    ', '.join(sorted(fresh_names - journal_names)))
            changes = resumed
            if record.get('phase') in ('complete', 'rolled-back'):
                journal_expected = record['files']
        elif not changes:
            require(new_cookie == old_cookie,
                    'source and patch cookie are unchanged only when candidate cookie matches')
            return False

        def build_clean():
            subprocess.run(base + ['build-clean'], check=True)

        patch_refresh.transaction(sdk, work, retained_source, changes, old_cookie, [],
                                  build_clean, cookie_bytes=new_cookie,
                                  expected_files=journal_expected)
    return True


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk-source', type=Path, required=True)
    p.add_argument('--bmake', type=Path, required=True)
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--native', action='store_true')
    p.add_argument('--expected-work', type=Path, required=True)
    p.add_argument('--make-arg', action='append', default=[])
    a = p.parse_args()
    scope = os.environ.get('CROSS_BULK_SOURCE_REFRESH_FILES', '').split()
    require(bool(scope), 'set CROSS_BULK_SOURCE_REFRESH_FILES to explicit relative source leaves')
    sys.path.insert(0, str(a.sdk_source / 'src'))
    from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep
    require(archive_metadata.ARCHIVE_METADATA_API == 1 and sourceprep.SOURCE_PREPARATION_API == 2,
            'incompatible selected SDK')
    sdk = dict(paths=paths, jsonio=jsonio, archive_metadata=archive_metadata, sourceprep=sourceprep)
    module_spec = importlib.util.spec_from_file_location(
        'stage_local_patch_refresh', Path(__file__).with_name('stage-local-patch-refresh.py'))
    patch_refresh = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(patch_refresh)
    args = (["USE_CROSS_COMPILE=no"] if a.native else []) + a.make_arg
    changed = source_refresh(sdk, patch_refresh, a.bmake, a.recipe, a.expected_work, args, scope)
    if changed:
        print('Refreshed the explicitly selected prepared source leaves; compatible objects retained.')
    else:
        print('Selected prepared source leaves and pkgsrc patch cookie are already current.')


if __name__ == '__main__':
    main()
