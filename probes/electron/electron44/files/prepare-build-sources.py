#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare one ordered Electron source layer, then optionally materialize it."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile

spec = importlib.util.spec_from_file_location('electron_bsd', Path(__file__).with_name('audit-bsd-overlay.py'))
bsd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bsd)
require = bsd.require


def digest(data):
    return None if data is None else hashlib.sha256(data).hexdigest()


def read_series(manifest, patch_root):
    value = json.loads(manifest.read_text())
    require(value.get('version') == 1 and value.get('stage') == 'after-pinned-electron-upstream-and-bsd-patches',
            'unsupported Electron build source series')
    require(isinstance(value.get('patches'), list) and value['patches'], 'source series is empty')
    rows, seen = [], set()
    for entry in value['patches']:
        require(set(entry) == {'path', 'root', 'strip'}, 'invalid source patch entry')
        name = bsd.relative(entry['path'])
        require(len(name.parts) == 1 and entry['path'] not in seen, 'duplicate or nested source patch')
        seen.add(entry['path'])
        directory = bsd.relative(entry['root']) if entry['root'] else PurePosixPath()
        require(type(entry['strip']) is int and entry['strip'] in (0, 1), 'unsupported patch strip level')
        filename = patch_root / name
        require(filename.is_file() and not filename.is_symlink(), 'source patch must be a regular recipe file')
        data = filename.read_bytes()
        targets = set()
        lines = data.decode().splitlines()
        for index, line in enumerate(lines[:-1]):
            if not (line.startswith('--- ') and lines[index + 1].startswith('+++ ')):
                continue
            old, new = line[4:].split()[0], lines[index + 1][4:].split()[0]
            for target in (old, new):
                if target == '/dev/null':
                    continue
                path = bsd.relative(target)
                require(len(path.parts) > entry['strip'], 'patch path is shorter than its strip level')
            if old != '/dev/null' and new != '/dev/null':
                old_path = str(PurePosixPath(*PurePosixPath(old).parts[entry['strip']:])).removesuffix('.orig')
                new_path = str(PurePosixPath(*PurePosixPath(new).parts[entry['strip']:]))
                require(old_path == new_path, 'source patch renames are unsupported')
            target = new if new != '/dev/null' else old
            path = PurePosixPath(*PurePosixPath(target).parts[entry['strip']:])
            # pkgsrc's .orig suffix is a preimage label, never an output path.
            if new == '/dev/null':
                path = PurePosixPath(str(path).removesuffix('.orig'))
            targets.add(str(directory / path))
        require(targets, 'source patch has no regular-file targets')
        rows.append(dict(entry, filename=filename, targets=targets, sha256=digest(data)))
    return rows


def prepare(workspace, pkgsrc, archive, destination, git, patch, patch_root, manifest):
    workspace = workspace.resolve(strict=True)
    patch_root = patch_root.resolve(strict=True)
    rows = read_series(manifest, patch_root)
    result = bsd.audit(workspace, pkgsrc, archive, destination, git, patch)
    fixture = destination / 'files'
    # The BSD auditor includes the actual pin and all original target preimages.
    # Add source files touched only by this recipe's subsequent patches.
    targets = set().union(*(row['targets'] for row in rows))
    sources, revisions = bsd.committed_sources(workspace, git, targets)
    for name, content in sources.items():
        path = fixture / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    overlay = bsd.overlay_files(archive, json.loads((bsd.DATA / 'manifest.json').read_text()))
    targets.update(overlay)
    targets.update(row['target'] for row in result['rows'] if row['status'] == 'applied')
    # These are the bytes permitted in the live workspace before materialization,
    # including paths created by the BSD layer and by the ordered source patches.
    originals, source_revisions = bsd.committed_sources(workspace, git, targets)
    log_root = destination / 'ordered-logs'
    log_root.mkdir()
    applied = []
    prepared_preimages = {}
    for row in rows:
        # Record only states reconstructed by this complete ordered recipe.
        # A live source may already contain a previously published prefix of
        # the series; arbitrary working-tree bytes remain invalid.
        for name in row['targets']:
            path, data = current_file(fixture, name)
            prepared_preimages.setdefault(name, set()).add(digest(data))
        directory = fixture / row['root']
        directory.mkdir(parents=True, exist_ok=True)
        command = [str(git), 'apply', '-p' + str(row['strip']), str(row['filename'])]
        output = ''
        for check in (True, False):
            argv = command[:2] + (['--check'] if check else []) + command[2:]
            env = os.environ.copy()
            for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
                env.pop(name, None)
            env['GIT_CEILING_DIRECTORIES'] = str(fixture.parent)
            process = subprocess.run(argv, cwd=directory, env=env, capture_output=True, text=True)
            output += process.stdout + process.stderr
            (log_root / (row['path'] + '.log')).write_text(output)
            require(process.returncode == 0, 'ordered source patch failed: ' + row['path'])
        applied.append({key: row[key] for key in ('path', 'root', 'strip', 'sha256')})
    paths = {}
    for name in sorted(targets):
        path = fixture / name
        require(not path.is_symlink(), 'source patch created a symbolic link: ' + name)
        data = path.read_bytes() if path.exists() else None
        paths[name] = dict(before=digest(originals.get(name)), after=digest(data))
        intermediate = prepared_preimages.get(name, set()) - {paths[name]['before'], paths[name]['after']}
        if intermediate:
            paths[name]['prepared_before'] = sorted(intermediate, key=lambda value: value or '')
    output = dict(version=1, source_revisions=source_revisions,
                  patches=applied, paths=paths, scope='prepared source bytes; no configure, compile or target execution')
    atomic_json(destination / 'prepared-sources.json', output)
    return output


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.' + path.name + '.', delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write('\n')
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def current_file(root, relative):
    path = root / bsd.relative(relative)
    for parent in [path, *path.parents]:
        if parent == root:
            break
        require(not parent.is_symlink(), 'materialization path contains a symlink: ' + relative)
    require(not path.exists() or path.is_file(), 'materialization target is not a regular file: ' + relative)
    return path, path.read_bytes() if path.exists() else None


def materialize(workspace, destination, result, *, git):
    workspace = workspace.resolve(strict=True)
    source = workspace / 'src'
    require(source.is_dir() and not source.is_symlink(), 'source root is not a real directory')
    for name, revision in result['source_revisions'].items():
        repository = workspace / bsd.relative(name)
        require(repository.resolve(strict=True) == repository and not repository.is_symlink(),
                'source repository path changed: ' + name)
        actual = bsd.git_bytes(git, repository, 'rev-parse', 'HEAD').decode().strip()
        require(actual == revision, 'source repository HEAD differs before materialization: ' + name)
    changes = []
    # Check the complete write set before the first mutation. A retry accepts
    # only exact committed bytes or states reconstructed by this recipe's order.
    for name, row in result['paths'].items():
        path, current = current_file(source, name)
        prepared, data = current_file(destination / 'files', name)
        require(digest(data) == row['after'], 'prepared source changed: ' + name)
        allowed = [row['before'], row['after'], *row.get('prepared_before', [])]
        require(digest(current) in allowed, 'source differs from committed/prepared bytes: ' + name)
        if digest(current) != row['after']:
            changes.append((path, data))
    for path, data in changes:
        if data is None:
            path.unlink()
            continue
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name + '.', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
        try:
            temporary.chmod(mode)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    atomic_json(workspace / 'source-inputs/ports-build-sources.json', result)
    return len(changes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'pkgsrc', 'archive', 'destination', 'git', 'patch', 'patch-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='materialize only after checking all source preimages')
    args = parser.parse_args()
    try:
        result = prepare(args.workspace, args.pkgsrc, args.archive, args.destination, args.git, args.patch,
                         args.patch_root, Path(__file__).with_name('source-series.json'))
        if args.apply:
            print('Materialized source files:', materialize(args.workspace, args.destination, result, git=args.git))
        print('Prepared ordered source patches:', len(result['patches']))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, 'Electron source preparation failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
