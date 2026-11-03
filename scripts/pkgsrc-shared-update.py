# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Narrow, exclusive refresh of selected outputs in a shared pkgsrc export."""
import copy
import fcntl
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def update(directory, ports, git, sdk, patch, package, selected_files, *, resume=False):
    directory, ports = Path(directory), Path(ports)
    identity = load(ports / 'scripts/pkgsrc-source-identity.py', 'update_identity')
    exporter = load(ports / 'scripts/prepare-pkgsrc.py', 'update_exporter')
    package = exporter.package_path(package, 'selected package')
    if (not directory.is_absolute() or directory.is_symlink() or not directory.is_dir() or
            not (directory / 'pkgsrc').is_dir() or (directory / 'pkgsrc').is_symlink()):
        raise ValueError('shared export must be an absolute real directory')
    selected_files = [str('/'.join(exporter.relative_parts(x, 'selected file'))) for x in selected_files]
    if len(set(selected_files)) != len(selected_files):
        raise ValueError('duplicate selected file')
    lock = directory / '.pkgsrc-update.lock'
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(lock, flags, 0o600)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError('update lock is not a regular file')
    with os.fdopen(fd, 'a+b') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _locked(directory, ports, git, sdk, patch, package, selected_files, identity, exporter, resume)


def _locked(directory, ports, git, sdk, patch, package, selected_files, ident, exp, resume):
    marker = directory / ident.SHARED_EXPORT_DIRTY
    pending = None
    if os.path.lexists(marker):
        if not resume or marker.is_symlink() or not marker.is_file():
            raise ValueError('shared export update is incomplete; use --resume after inspection')
        pending = json.loads(marker.read_text())
        if pending.get('package') != package or pending.get('files') != selected_files:
            raise ValueError('resume selection differs from interrupted update')
    elif resume:
        raise ValueError('no incomplete shared export update to resume')
    receipt_path = directory / ident.SHARED_EXPORT_RECEIPT
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError('missing shared export receipt')
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('format') != ident.SHARED_EXPORT_FORMAT or receipt.get('version') not in (2, 3):
        raise ValueError('unsupported shared export receipt')
    if pending is not None:
        recorded = pending.get('previous_receipt')
        if not isinstance(recorded, dict) or not isinstance(recorded.get('identity'), dict):
            raise ValueError('invalid interrupted update marker')
        if receipt != recorded and not ident.equivalent_export_inputs(
                receipt.get('identity'), pending.get('new_identity')):
            raise ValueError('receipt differs from interrupted update')
        receipt = recorded
    previous = receipt['identity']
    if receipt['version'] == 3:
        raw = json.dumps(receipt.get('inputs'), sort_keys=True, separators=(',', ':')).encode()
        if hashlib.sha256(raw).hexdigest() != previous.get('export_inputs_sha256'):
            raise ValueError('invalid previous input snapshot')
        entries = receipt.get('dirty_inputs')
        if not isinstance(entries, dict):
            raise ValueError('invalid dirty input inventory')
        for name, entry in entries.items():
            exp.relative_parts(name, 'dirty input path')
            if (not isinstance(entry, dict) or set(entry) != {'sha256', 'mode'} or
                    not isinstance(entry['sha256'], str) or
                    re.fullmatch('[0-9a-f]{64}', entry['sha256']) is None or
                    type(entry['mode']) is not int or entry['mode'] not in (0o644, 0o755)):
                raise ValueError('invalid dirty input inventory entry')
    root, _, snapshot, run = ident.export_inputs(ports, git, sdk)
    current = ident.export_identity_from_payload(snapshot, run(root, 'rev-parse', 'HEAD').decode('ascii'), patch)
    if pending is not None and not ident.equivalent_export_inputs(pending.get('new_identity'), current):
        raise ValueError('inputs changed since interrupted update')
    if previous['upstream'] != current['upstream'] or previous['patch'] != current['patch']:
        raise ValueError('upstream pin or patch selection changed; update refused')
    oldrev = previous['ports_commit']
    old_inputs = receipt.get('inputs') if receipt['version'] == 3 else None
    dirty_before = receipt.get('dirty_inputs', {})
    cache = directory / '.pkgsrc-update-inputs'
    def git_call(*args, check=True):
        return subprocess.run([git, '-C', str(ports), *args], check=check, capture_output=True)
    def snapshot_hash(inputs, name):
        if inputs is None:
            return None
        if name in inputs['files']:
            return inputs['files'][name]
        for tree, rows in inputs['trees'].items():
            if name.startswith(tree + '/'):
                row = rows.get(name[len(tree) + 1:])
                if row and row.get('kind') == 'file':
                    return row['sha256']
        return None
    def old_file(name):
        result = git_call('show', oldrev + ':' + name, check=False)
        expected = snapshot_hash(old_inputs, name)
        if expected is not None and (not isinstance(expected, str) or re.fullmatch('[0-9a-f]{64}', expected) is None):
            raise ValueError('invalid previous input digest: ' + name)
        if result.returncode == 0 and (expected is None or hashlib.sha256(result.stdout).hexdigest() == expected):
            return result.stdout
        if expected is None:
            return None
        record = dirty_before.get(name)
        if not isinstance(record, dict) or record.get('sha256') != expected:
            raise ValueError('previous dirty input is unavailable: ' + name)
        if cache.is_symlink() or not cache.is_dir():
            raise ValueError('previous dirty input cache is unavailable')
        blob = cache / expected
        if blob.is_symlink() or not blob.is_file() or stat.S_IMODE(blob.stat().st_mode) != 0o600:
            raise ValueError('invalid previous dirty input cache: ' + name)
        content = blob.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('previous dirty input cache hash differs: ' + name)
        return content
    old_conf = old_file('pkgsrc/export.conf')
    if old_conf is None:
        raise ValueError('missing historical export configuration')
    def records(data):
        result = []
        for line in data.decode('utf-8').splitlines():
            fields = line.split('\t')
            if line and not line.startswith('#'):
                result.append(fields)
        return result
    old_records = records(old_conf)
    new_records = records((ports / 'pkgsrc/export.conf').read_bytes())
    def references(rows):
        result = {'scripts/prepare-pkgsrc.py', 'pkgsrc/export.conf', 'pkgsrc/replaces'}
        for row in rows:
            if row[0] in ('patch', 'git-apply', 'recipe-patch', 'file'):
                result.add(row[1])
            if row[0] == 'git-apply':
                result.add(row[2])
        return result
    old_refs = references(old_records)
    changed = set(git_call('diff', '--name-only', oldrev, '--').stdout.decode().splitlines())
    current_refs = set(snapshot['files'])
    changed.update(current_refs - old_refs)
    if old_inputs is not None:
        changed.update(name for name in set(snapshot['files']) | set(old_inputs['files'])
                       if snapshot['files'].get(name) != old_inputs['files'].get(name))
        for tree in set(snapshot['trees']) | set(old_inputs['trees']):
            before = old_inputs['trees'].get(tree, {})
            after = snapshot['trees'].get(tree, {})
            changed.update(tree + '/' + name for name in set(before) | set(after)
                           if before.get(name) != after.get(name) and
                           ((before.get(name) or after.get(name)).get('kind') != 'directory'))
    changed.update(git_call('ls-files', '--others', '--exclude-standard').stdout.decode().splitlines())
    if old_inputs is not None:
        def input_row(inputs, name, historical):
            for tree, rows in inputs['trees'].items():
                if name.startswith(tree + '/'):
                    row = rows.get(name[len(tree) + 1:])
                    if row is not None:
                        return row
            sha = inputs['files'].get(name)
            if sha is None:
                return None
            if historical:
                mode = dirty_before.get(name, {}).get('mode')
                if mode is None:
                    row = git_call('ls-tree', oldrev, '--', name).stdout.split()
                    if not row or row[0] not in (b'100644', b'100755'):
                        raise ValueError('previous input mode unavailable: ' + name)
                    mode = 0o755 if row[0] == b'100755' else 0o644
            else:
                source = exp.source_path(ports, name, 'current export input')
                mode = stat.S_IMODE(source.stat().st_mode)
            return {'kind': 'file', 'sha256': sha, 'mode': mode}
        changed = {name for name in changed
                   if input_row(old_inputs, name, True) != input_row(snapshot, name, False)}
    changes = {}
    for name in changed:
        if name not in old_refs and name not in current_refs and not any(name.startswith(t + '/') for t in snapshot['trees']):
            continue
        before = old_file(name)
        if before is None:
            mode = None
        else:
            row = git_call('ls-tree', oldrev, '--', name).stdout.split()
            if name in dirty_before:
                mode = dirty_before[name].get('mode')
            elif row and row[0] in (b'100644', b'100755'):
                mode = 0o755 if row[0] == b'100755' else 0o644
            else:
                raise ValueError('unsupported historical input type: ' + name)
        changes[name] = (before, mode, name in old_refs and before is not None)
    if receipt['version'] == 2:
        old_snapshot = ident.reconstruct_legacy_payload(snapshot, changes, previous['export_inputs_sha256'])
    else:
        old_snapshot = receipt['inputs']
        rebuilt = ident.reconstruct_legacy_payload(snapshot, changes, previous['export_inputs_sha256'])
        if rebuilt != old_snapshot:
            raise ValueError('previous input snapshot differs')
    def file_map(rows):
        result = {}
        for row in rows:
            if row[0] != 'file':
                continue
            if len(row) != 3 or row[2] in result:
                raise ValueError('invalid or duplicate declared file output')
            exp.relative_parts(row[1], 'file source')
            exp.relative_parts(row[2], 'file output')
            result[row[2]] = row[1]
        return result
    old_files, new_files = file_map(old_records), file_map(new_records)
    if any(name == package or name.startswith(package + '/') for name in selected_files):
        raise ValueError('selected file overlaps selected package')
    if any(name not in old_files and name not in new_files for name in selected_files):
        raise ValueError('selected file is not a declared export output')
    selected_sources = {mapping[name] for mapping in (old_files, new_files)
                        for name in selected_files if name in mapping}
    def read_source(name, old):
        if old and name in changed:
            data = old_file(name)
            if data is None:
                raise ValueError('missing historical source: ' + name)
            return data
        path = exp.source_path(ports, name, 'update source')
        if not path.is_file():
            raise ValueError('update source is not a regular file: ' + name)
        return path.read_bytes()
    patch_names = {row[1] for rows in (old_records, new_records) for row in rows
                   if row[0] in ('patch', 'git-apply')}
    scoped_patches = set()
    for name in changed & patch_names:
        for old in (True, False):
            if old and old_file(name) is None:
                continue
            if not old and not (ports / name).is_file():
                continue
            data = read_source(name, old)
            sections = ident._update_patch_sections(data)
            if sections is None or any(not all(x.startswith(package + '/') for x in paths)
                                       for paths, _ in sections):
                raise ValueError('changed patch extends outside selected package: ' + name)
        scoped_patches.add(name)
    for name in changes:
        if name == 'pkgsrc/export.conf' or name in selected_sources or name in scoped_patches:
            continue
        if name.startswith('pkgsrc/' + package + '/'):
            continue
        raise ValueError('changed export input outside selected outputs: ' + name)
    def unaffected(rows):
        return [row for row in rows if not (row[0] in ('patch', 'git-apply') and row[1] in scoped_patches)
                and not (row[0] == 'file' and len(row) == 3 and row[2] in selected_files)]
    if unaffected(old_records) != unaffected(new_records):
        raise ValueError('export configuration changed outside selected outputs')
    for _, source in exp.configuration(ports)[0]:
        if source.is_relative_to(ports / 'pkgsrc' / package):
            raise ValueError('overlay recipe update is not supported by this scoped exporter')
    from emberbsd_sdk import inventory
    with tempfile.TemporaryDirectory(prefix='.pkgsrc-update-stage-', dir=directory.parent) as temp:
        temp = Path(temp)
        def prepare(label, rows, old):
            stage = temp / label
            stage.mkdir()
            archive = temp / (label + '.tar')
            with archive.open('wb') as stream:
                subprocess.run([git, '-C', str(ports / 'upstream/pkgsrc'), 'archive',
                                '--format=tar', previous['upstream'], package], check=True, stdout=stream)
            exp.extract_archive(archive, stage)
            if not (stage / package / 'Makefile').is_file():
                raise ValueError('selected upstream package is missing')
            for row in rows:
                if row[0] not in ('patch', 'git-apply'):
                    if row[0] in ('recipe', 'recipe-patch') and len(row) > 2 and row[2] == package:
                        raise ValueError('selected recipe overlay is unsupported')
                    continue
                data = read_source(row[1], old)
                paths = ident._patch_targets_bytes(data)
                if paths is None:
                    raise ValueError('opaque patch targets: ' + row[1])
                if not any(path.startswith(package + '/') for path in paths):
                    continue
                if row[0] == 'git-apply':
                    if any(not path.startswith(package + '/') for path in paths) or b'GIT binary patch' in data:
                        raise ValueError('git patch extends outside selected package')
                    subprocess.run([git, '-C', str(stage), 'apply', '--whitespace=nowarn', '-'], input=data, check=True)
                else:
                    sections = ident._update_patch_sections(data)
                    if sections is None:
                        raise ValueError('opaque unified patch: ' + row[1])
                    matching = []
                    for names, part in sections:
                        if any(name.startswith(package + '/') for name in names):
                            if any(not name.startswith(package + '/') for name in names):
                                raise ValueError('patch section crosses selected package')
                            matching.append(part)
                    if matching:
                        subprocess.run([patch, '-f', '-E', '-d', str(stage), '-p1', '-F', '0', '-V', 'none'],
                                       input=b''.join(matching), check=True, stdout=subprocess.DEVNULL)
            return stage / package
        old_pkg = prepare('old', old_records, True)
        new_pkg = prepare('new', new_records, False)
        live = exp.destination_parent(directory / 'pkgsrc', package)
        old_tree = inventory.snapshot_installed_tree(str(old_pkg))
        new_tree = inventory.snapshot_installed_tree(str(new_pkg))
        live_tree = inventory.snapshot_installed_tree(str(live))
        if pending is None and old_tree != live_tree:
            raise ValueError('selected live package differs from the previous export')
        if pending is not None:
            for name in set(old_tree) | set(new_tree) | set(live_tree):
                if live_tree.get(name) not in (old_tree.get(name), new_tree.get(name)):
                    raise ValueError('interrupted package differs from both recorded states: ' + name)
        if any(row['kind'] != 'file' for rows in (old_tree, new_tree) for row in rows.values()
               if row['kind'] != 'directory'):
            raise ValueError('selected package has unsupported links or special files')
        file_changes = []
        for name in selected_files:
            destination = exp.destination_parent(directory / 'pkgsrc', name)
            before = read_source(old_files[name], True) if name in old_files else None
            after = read_source(new_files[name], False) if name in new_files else None
            old_source = old_files.get(name)
            old_row = git_call('ls-tree', oldrev, '--', old_source).stdout.split() if old_source else []
            old_mode = dirty_before.get(old_source, {}).get('mode')
            if old_mode is None and old_row:
                old_mode = 0o755 if old_row[0] == b'100755' else 0o644
            source = new_files.get(name)
            mode = (stat.S_IMODE((ports / source).stat().st_mode) & ~0o022) if source else None
            if os.path.lexists(destination):
                if destination.is_symlink() or not destination.is_file():
                    raise ValueError('selected live file has unsupported type: ' + name)
                actual = (destination.read_bytes(), stat.S_IMODE(destination.stat().st_mode))
                permitted = [(before, old_mode)]
                if pending is not None:
                    permitted.append((after, mode))
                if actual not in permitted:
                    raise ValueError('selected live file differs: ' + name)
            elif before is not None and not (pending is not None and after is None):
                raise ValueError('selected live file is missing: ' + name)
            file_changes.append((destination, after, mode))
        for name in set(old_tree) & set(new_tree):
            if old_tree[name]['kind'] != new_tree[name]['kind']:
                raise ValueError('selected package entry changes type: ' + name)
        input_names = set(snapshot['files'])
        for tree, rows in snapshot['trees'].items():
            input_names.update(tree + '/' + name for name, row in rows.items() if row['kind'] == 'file')
        dirty = set(git_call('diff', '--name-only', 'HEAD', '--').stdout.decode().splitlines())
        dirty.update(git_call('ls-files', '--others', '--exclude-standard').stdout.decode().splitlines())
        dirty.update(git_call('ls-files', '--others', '-i', '--exclude-standard').stdout.decode().splitlines())
        dirty.update(current_refs - old_refs)
        dirty_inputs, dirty_content = {}, {}
        for name in sorted(dirty & input_names):
            source = exp.source_path(ports, name, 'dirty export input')
            if source.is_symlink() or not source.is_file():
                raise ValueError('dirty export input is not a regular file: ' + name)
            content = source.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            if sha != snapshot_hash(snapshot, name):
                raise ValueError('dirty export input changed while read: ' + name)
            mode = stat.S_IMODE(source.stat().st_mode)
            if mode not in (0o644, 0o755):
                raise ValueError('unsupported dirty export input mode: ' + name)
            tracked = git_call('show', 'HEAD:' + name, check=False)
            tree = git_call('ls-tree', 'HEAD', '--', name, check=False).stdout.split()
            tracked_mode = (0o755 if tree[0] == b'100755' else 0o644) if tree and tree[0] in (b'100644', b'100755') else None
            if tracked.returncode == 0 and tracked.stdout == content and tracked_mode == mode:
                continue
            dirty_inputs[name] = {'sha256': sha, 'mode': mode}
            dirty_content[sha] = content
        if not ident.equivalent_export_inputs(current, ident.export_identity(ports, git, sdk, patch)):
            raise ValueError('export inputs changed during update preparation')
        def sync_dir(path):
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

        if pending is None:
            with marker.open('x') as stream:
                json.dump({'package': package, 'files': selected_files,
                           'previous_receipt': receipt, 'new_identity': current}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            sync_dir(directory)
        def replace(path, content, mode):
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='.pkgsrc-update-', dir=path.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(name, mode)
                os.replace(name, path)
                sync_dir(path.parent)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        if dirty_content:
            if os.path.lexists(cache) and (cache.is_symlink() or not cache.is_dir()):
                raise ValueError('invalid dirty input cache')
            cache.mkdir(mode=0o700, exist_ok=True)
            sync_dir(directory)
            for sha, content in dirty_content.items():
                blob = cache / sha
                if os.path.lexists(blob):
                    if blob.is_symlink() or not blob.is_file() or stat.S_IMODE(blob.stat().st_mode) != 0o600 or hashlib.sha256(blob.read_bytes()).hexdigest() != sha:
                        raise ValueError('existing dirty input cache differs')
                else:
                    replace(blob, content, 0o600)
        # Explicit files are published first, so an updated verifier sees the marker.
        for path, content, mode in file_changes:
            if content is None:
                path.unlink(missing_ok=True)
                sync_dir(path.parent)
            elif not path.exists() or path.read_bytes() != content or stat.S_IMODE(path.stat().st_mode) != mode:
                replace(path, content, mode)
        for name in sorted(set(old_tree) | set(new_tree), key=lambda x: (x.count('/'), x), reverse=True):
            before, after = live_tree.get(name), new_tree.get(name)
            target = exp.destination_parent(directory / 'pkgsrc', package + '/' + name)
            if before == after:
                continue
            if after is None:
                if before['kind'] == 'directory':
                    target.rmdir()
                else:
                    target.unlink()
                sync_dir(target.parent)
            elif after['kind'] == 'file':
                if before is not None and before['kind'] != 'file':
                    raise ValueError('package entry changed type')
                replace(target, (new_pkg / name).read_bytes(), after['mode'])
            elif after['kind'] == 'directory':
                if before is not None:
                    raise ValueError('package directory changed')
                target.mkdir(parents=True, exist_ok=True)
                sync_dir(target.parent)
        updated = {'format': ident.SHARED_EXPORT_FORMAT, 'version': 3, 'identity': current,
                   'material': {name: ident.material_snapshot(directory / 'pkgsrc' / name)
                                for name in ident.SHARED_EXPORT_MATERIAL}, 'inputs': snapshot,
                   'dirty_inputs': dirty_inputs}
        replace(receipt_path, (json.dumps(updated, sort_keys=True) + '\n').encode(), 0o644)
        marker.unlink()
        sync_dir(directory)
        if cache.is_dir() and not cache.is_symlink():
            for blob in cache.iterdir():
                if blob.name not in dirty_content and blob.is_file() and not blob.is_symlink():
                    blob.unlink()
            sync_dir(cache)
        return updated
