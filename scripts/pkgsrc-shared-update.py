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
import posixpath
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
    class PatchSelection:
        def command(self, role):
            if role != 'patch':
                raise ValueError('unexpected patch capability role')
            return (patch,)
    def patch_probe(argv):
        return subprocess.run(argv, check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).stdout
    patch_options = exporter.patch_safety_options(PatchSelection(), patch_probe)
    packages = [exporter.package_path(item, 'selected package') for item in ([package] if isinstance(package, str) else package)]
    if not packages or len(set(packages)) != len(packages):
        raise ValueError('empty or duplicate selected package')
    packages.sort()
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
        return _locked(directory, ports, git, sdk, patch, packages, selected_files, identity, exporter, resume, patch_options)


def _locked(directory, ports, git, sdk, patch, packages, selected_files, ident, exp, resume, patch_options):
    marker = directory / ident.SHARED_EXPORT_DIRTY
    pending = None
    if os.path.lexists(marker):
        if not resume or marker.is_symlink() or not marker.is_file():
            raise ValueError('shared export update is incomplete; use --resume after inspection')
        pending = json.loads(marker.read_text())
        previous_packages = pending.get('packages', [pending.get('package')])
        if previous_packages != packages or pending.get('files') != selected_files:
            raise ValueError('resume selection differs from interrupted update')
    elif resume:
        raise ValueError('no incomplete shared export update to resume')
    receipt_path = directory / ident.SHARED_EXPORT_RECEIPT
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError('missing shared export receipt')
    receipt = json.loads(receipt_path.read_text())
    ident.validate_shared_receipt(receipt)
    if pending is not None:
        recorded = pending.get('previous_receipt')
        if not isinstance(recorded, dict) or not isinstance(recorded.get('identity'), dict):
            raise ValueError('invalid interrupted update marker')
        if receipt != recorded and receipt != pending.get('expected_new_receipt'):
            raise ValueError('receipt differs from interrupted update')
        receipt = recorded
    ident.validate_shared_receipt(receipt)
    previous = receipt['identity']
    root, _, snapshot, run = ident.export_inputs(ports, git, sdk)
    current = ident.export_identity_from_payload(snapshot, run(root, 'rev-parse', 'HEAD').decode('ascii'), patch)
    if pending is not None and not ident.equivalent_export_inputs(pending.get('new_identity'), current):
        raise ValueError('inputs changed since interrupted update')
    if previous['upstream'] != current['upstream']:
        raise ValueError('upstream pin changed; update refused')
    oldrev = previous['ports_commit']
    old_inputs = receipt['inputs']
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
                if row and row.get('kind') in ('file', 'link'):
                    return row['target_sha256'] if row['kind'] == 'link' else row['sha256']
        return None
    # Read Git modes once. Source links are materialized by the exporter.
    tree_cache = {}
    def historical_tree(revision):
        if revision not in tree_cache:
            entries = {}
            for record in git_call('ls-tree', '-rz', revision).stdout.split(b'\0'):
                if record:
                    metadata, name = record.split(b'\t', 1)
                    entries[name.decode('utf-8')] = metadata.split()
            tree_cache[revision] = entries
        return tree_cache[revision]
    old_blobs = {}
    blob_cache = {oldrev: old_blobs}
    def historical_blob(name, revision=oldrev):
        blobs = blob_cache.setdefault(revision, {})
        if name not in blobs:
            entry = historical_tree(revision).get(name)
            blobs[name] = (git_call('cat-file', 'blob', entry[2].decode('ascii')).stdout
                           if entry and entry[1] == b'blob' else None)
        return blobs[name]
    def historical_file(name, revision=oldrev):
        entries = historical_tree(revision)
        seen = set()
        while True:
            if name in seen or len(seen) >= 64:
                raise ValueError('historical input link cycle: ' + name)
            seen.add(name)
            parts = name.split('/')
            for index in range(1, len(parts) + 1):
                prefix = '/'.join(parts[:index])
                entry = entries.get(prefix)
                if entry and entry[0] == b'120000':
                    target = historical_blob(prefix, revision).decode('utf-8')
                    if (not target or posixpath.isabs(target) or '\\' in target or
                            any(ord(char) < 32 or ord(char) == 127 for char in target)):
                        raise ValueError('unsafe historical input link: ' + prefix)
                    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(prefix), target))
                    if resolved == '..' or resolved.startswith('../'):
                        raise ValueError('historical input link leaves Ports: ' + prefix)
                    name = posixpath.join(resolved, *parts[index:])
                    break
            else:
                entry = entries.get(name)
                if entry is None:
                    return None, None
                if entry[0] not in (b'100644', b'100755'):
                    raise ValueError('historical input is not a regular file: ' + name)
                return historical_blob(name, revision), 0o755 if entry[0] == b'100755' else 0o644
    def old_mode(name):
        return dirty_before[name]['mode'] if name in dirty_before else historical_file(name)[1]
    def old_file(name):
        content, _ = historical_file(name)
        expected = snapshot_hash(old_inputs, name)
        if expected is not None and (not isinstance(expected, str) or re.fullmatch('[0-9a-f]{64}', expected) is None):
            raise ValueError('invalid previous input digest: ' + name)
        if content is not None and (expected is None or hashlib.sha256(content).hexdigest() == expected):
            return content
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
    # Link rows store lstat mode. The copied file uses its target's mode.
    # Include mode-only owner changes without changing existing receipt hashes.
    link_inputs = {tree + '/' + name for inputs in (old_inputs, snapshot) if inputs
                   for tree, rows in inputs['trees'].items()
                   for name, row in rows.items() if row['kind'] == 'link'}
    material_mode_changes = set()
    for name in link_inputs:
        source = ports / name
        current_mode = (stat.S_IMODE(source.stat().st_mode) & ~0o022) if source.is_file() else None
        if old_mode(name) != current_mode:
            material_mode_changes.add(name)
    changed.update(material_mode_changes)
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
                mode = old_mode(name)
            else:
                source = exp.source_path(ports, name, 'current export input')
                mode = stat.S_IMODE(source.stat().st_mode) & ~0o022
            return {'kind': 'file', 'sha256': sha, 'mode': mode}
        changed = {name for name in changed
                   if name in material_mode_changes or
                   input_row(old_inputs, name, True) != input_row(snapshot, name, False)}
    changes = {}
    for name in changed:
        if name not in old_refs and name not in current_refs and not any(name.startswith(t + '/') for t in snapshot['trees']):
            continue
        before = old_file(name)
        if before is None:
            mode = None
        else:
            mode = old_mode(name)
        changes[name] = (before, mode, name in old_refs and before is not None)
    old_snapshot = receipt['inputs']
    selected_recipes = {name: source.relative_to(ports).as_posix()
                        for name, source in exp.configuration(ports)[0] if name in packages}
    overlays = {package: selected_recipes.get(package) for package in packages}
    for package, overlay in overlays.items():
        if overlay is not None and overlay not in snapshot['trees']:
            raise ValueError('selected recipe source layout changed')
        if overlay is None and 'pkgsrc/' + package in old_snapshot['trees']:
            raise ValueError('selected recipe source layout changed')
        for rows in ([old_snapshot['trees'].get(overlay, {}), snapshot['trees'][overlay]] if overlay else []):
            if any(row['kind'] not in ('file', 'directory', 'link') for row in rows.values()):
                raise ValueError('selected recipe contains unsupported links')
    def selected_output(name):
        return any(name.startswith(package + '/') for package in packages)
    for tree in set(old_snapshot['trees']) | set(snapshot['trees']):
        before, after = old_snapshot['trees'].get(tree, {}), snapshot['trees'].get(tree, {})
        for name in set(before) | set(after):
            old_row, new_row = before.get(name), after.get(name)
            if old_row == new_row or (old_row or new_row).get('kind') != 'directory':
                continue
            changed_directory = tree + '/' + name
            if not any(overlay and (changed_directory == overlay or changed_directory.startswith(overlay + '/') or (old_row is None and overlay.startswith(changed_directory + '/'))) for overlay in overlays.values()):
                raise ValueError('directory input changed outside selected recipe: ' + changed_directory)
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
    def read_global_patch(name, old):
        if old and name in changed:
            data = old_file(name)
            if data is None:
                raise ValueError('missing historical patch: ' + name)
            return data
        return exp.source_path(ports, name, 'patch source').read_bytes()
    if any(name in packages or selected_output(name) for name in selected_files):
        raise ValueError('selected file overlaps selected package')
    global_files = set(selected_files) - set(old_files) - set(new_files)
    for name in global_files:
        touched = False
        for rows in (old_records, new_records):
            for row in rows:
                if row[0] not in ('patch', 'git-apply'):
                    continue
                data = read_global_patch(row[1], rows is old_records)
                paths = ident._patch_targets_bytes(data)
                if paths is None:
                    raise ValueError('opaque patch targets: ' + row[1])
                touched |= name in paths
        if not touched:
            raise ValueError('selected file is not a declared or patched export output: ' + name)
    selected_sources = {mapping[name] for mapping in (old_files, new_files)
                        for name in selected_files if name in mapping}
    selected_sources.update(source for mapping in (old_files, new_files)
                            for name, source in mapping.items() if selected_output(name))
    recipe_patch_sources = {row[1] for rows in (old_records, new_records) for row in rows
                            if row[0] == 'recipe-patch' and len(row) == 4 and row[2] in packages}
    for rows in (old_records, new_records):
        for row in rows:
            if (row[1] in changed & recipe_patch_sources and not
                    ((row[0] == 'recipe-patch' and row[2] in packages) or
                     (row[0] == 'file' and (row[2] in selected_files or selected_output(row[2]))))):
                raise ValueError('recipe patch source has other export consumers')
    for source in changed & selected_sources:
        for mapping in (old_files, new_files):
            for output, owner in mapping.items():
                if owner == source and output not in selected_files and not selected_output(output):
                    raise ValueError('selected file source has another export consumer: ' + source)
        for rows in (old_records, new_records):
            for row in rows:
                if (len(row) > 1 and row[1] == source and row[0] != 'file' and not
                        (row[0] == 'recipe-patch' and row[2] in packages)):
                    raise ValueError('selected file source has another export consumer: ' + source)
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
            if sections is None or any(not all(selected_output(x) or x in global_files for x in paths)
                                       for paths, _ in sections):
                raise ValueError('changed patch extends outside selected package: ' + name)
        scoped_patches.add(name)
    old_replaces = (old_file('pkgsrc/replaces') or b'').decode('utf-8')
    new_replaces = (ports / 'pkgsrc/replaces').read_text() if (ports / 'pkgsrc/replaces').is_file() else ''
    def replacements(text):
        return {line.strip() for line in text.splitlines() if line.strip() and not line.startswith('#')}
    added = replacements(new_replaces) - replacements(old_replaces)
    removed = replacements(old_replaces) - replacements(new_replaces)
    if removed or not added.issubset(set(packages)) or any(overlays.get(p) != 'pkgsrc/' + p for p in added):
        raise ValueError('replacement changes outside selected new overlays')
    for name in changes:
        if (name == 'pkgsrc/replaces' or name == 'pkgsrc/export.conf' or name in selected_sources or
                name in scoped_patches or name in recipe_patch_sources):
            continue
        if any((overlay and name.startswith(overlay + '/')) or name.startswith('pkgsrc/' + package + '/')
               for package, overlay in overlays.items()):
            continue
        raise ValueError('changed export input outside selected outputs: ' + name)
    def unaffected(rows):
        return [row for row in rows if not (row[0] in ('patch', 'git-apply') and row[1] in scoped_patches)
                and not (row[0] == 'recipe-patch' and len(row) == 4 and row[2] in packages)
                and not (row[0] == 'file' and len(row) == 3 and
                         (row[2] in selected_files or selected_output(row[2])))]
    if unaffected(old_records) != unaffected(new_records):
        raise ValueError('export configuration changed outside selected outputs')
    from emberbsd_sdk import inventory
    old_patch_targets = {}
    with tempfile.TemporaryDirectory(prefix='.pkgsrc-update-stage-', dir=directory.parent) as temp:
        temp = Path(temp)
        def prepare(label, rows, old, package, overlay, *, global_file=False):
            stage = temp / label
            stage.mkdir()
            archive = temp / (label + '.tar')
            upstream_path = package if global_file else package + '/Makefile'
            upstream = subprocess.run([git, '-C', str(ports / 'upstream/pkgsrc'), 'cat-file', '-e',
                                       previous['upstream'] + ':' + upstream_path],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            if old and not global_file and overlay is not None and overlay not in old_snapshot['trees'] and not upstream:
                for row in rows:
                    if row[0] == 'recipe-patch' and row[2] == package:
                        raise ValueError('old export has a recipe patch for absent package: ' + package)
                    if row[0] == 'file' and (row[2] == package or row[2].startswith(package + '/')):
                        raise ValueError('old export has a file for absent package: ' + package)
                    if row[0] in ('patch', 'git-apply'):
                        if row[1] not in old_patch_targets:
                            old_patch_targets[row[1]] = ident._patch_targets_bytes(read_global_patch(row[1], True))
                        targets = old_patch_targets[row[1]]
                        if targets is None or any(x == package or x.startswith(package + '/') for x in targets):
                            raise ValueError('old export patch may affect absent package: ' + package)
                return None
            if upstream:
                with archive.open('wb') as stream:
                    subprocess.run([git, '-C', str(ports / 'upstream/pkgsrc'), 'archive',
                                    '--format=tar', previous['upstream'], package], check=True, stdout=stream)
                exp.extract_archive(archive, stage)
            if global_file:
                entry = subprocess.run([git, '-C', str(ports / 'upstream/pkgsrc'), 'ls-tree',
                                        previous['upstream'], '--', package], capture_output=True, check=True).stdout
                if entry:
                    if not entry.startswith((b'100644 blob ', b'100755 blob ')) or (stage / package).is_symlink() or not (stage / package).is_file():
                        raise ValueError('selected upstream file is not regular: ' + package)
                else:
                    # A global patch can create a file absent from upstream.
                    # Replay the complete old/new chain against an absent file;
                    # the output must still be regular and match the live tree.
                    parent = package.rpartition('/')[0]
                    if parent:
                        exp.ensure_destination_directory(stage, parent)
            elif overlay is not None and (not old or overlay in old_snapshot['trees']):
                replaces = old_file('pkgsrc/replaces') if old else (
                    (ports / 'pkgsrc/replaces').read_bytes() if (ports / 'pkgsrc/replaces').is_file() else b'')
                replacements = {line.strip() for line in (replaces or b'').decode('utf-8').splitlines()
                                if line.strip() and not line.startswith('#')}
                if upstream != (package in replacements):
                    raise ValueError('selected recipe replacement conflicts with pkgsrc/replaces')
                target = stage / package
                if target.exists():
                    shutil.rmtree(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                if old:
                    target.mkdir()
                    source_rows = old_snapshot['trees'][overlay]
                    names = []
                    for relative, entry in source_rows.items():
                        exp.relative_parts(relative, 'historical recipe path')
                        if entry['kind'] in ('file', 'link'):
                            names.append(overlay + '/' + relative)
                    if names:
                        request = b''.join((oldrev + ':' + name + '\n').encode('utf-8') for name in names)
                        batch = subprocess.run([git, '-C', str(ports), 'cat-file', '--batch'],
                                               input=request, capture_output=True, check=True).stdout
                        offset = 0
                        for name in names:
                            end = batch.find(b'\n', offset)
                            if end < 0:
                                raise ValueError('truncated historical recipe Git response')
                            header = batch[offset:end].split()
                            offset = end + 1
                            if header and header[-1] == b'missing':
                                old_blobs[name] = None
                                continue
                            if len(header) != 3 or header[1] != b'blob' or not header[2].isdigit():
                                raise ValueError('invalid historical recipe Git response')
                            size = int(header[2])
                            if offset + size >= len(batch) or batch[offset + size:offset + size + 1] != b'\n':
                                raise ValueError('truncated historical recipe Git blob')
                            old_blobs[name] = batch[offset:offset + size]
                            offset += size + 1
                        if offset != len(batch):
                            raise ValueError('unexpected historical recipe Git response')
                    for relative, entry in sorted(source_rows.items(), key=lambda item: (item[0].count('/'), item[0])):
                        exp.relative_parts(relative, 'historical recipe path')
                        output = target / relative
                        if entry['kind'] == 'directory':
                            output.mkdir()
                            output.chmod(entry['mode'])
                        elif entry['kind'] in ('file', 'link'):
                            name = overlay + '/' + relative
                            data = old_file(name)
                            expected = entry['target_sha256'] if entry['kind'] == 'link' else entry['sha256']
                            if data is None or hashlib.sha256(data).hexdigest() != expected:
                                raise ValueError('historical recipe file differs: ' + relative)
                            output.write_bytes(data)
                            mode = old_mode(name) if entry['kind'] == 'link' else entry['mode']
                            output.chmod(mode & ~0o022)
                else:
                    shutil.copytree(ports / overlay, target, copy_function=exp.copy_file)
            elif not upstream:
                raise ValueError('selected upstream package is missing')
            for row in rows:
                if not global_file and row[0] == 'recipe-patch' and len(row) == 4 and row[2] == package:
                    name = exp.relative_parts(row[3], 'recipe patch name')
                    if len(name) != 1 or not name[0].startswith('patch-'):
                        raise ValueError('invalid recipe patch name')
                    dest = exp.ensure_destination_directory(stage, package + '/patches') / name[0]
                    if os.path.lexists(dest):
                        raise ValueError('recipe patch collision')
                    content = read_source(row[1], old)
                    dest.write_bytes(content)
                    source_mode = dirty_before.get(row[1], {}).get('mode') if old else None
                    if source_mode is None and old:
                        source_mode = old_mode(row[1])
                    if source_mode is None:
                        source_mode = stat.S_IMODE((ports / row[1]).stat().st_mode)
                    dest.chmod(source_mode & ~0o022)
                    distinfo = exp.destination_parent(stage, package + '/distinfo')
                    if distinfo.is_symlink() or not distinfo.is_file():
                        raise ValueError('recipe distinfo is not a regular file')
                    with distinfo.open('a', encoding='utf-8') as stream:
                        stream.write(f'SHA1 ({name[0]}) = {exp.patch_sha1(dest)}\n')
                    continue
                if row[0] not in ('patch', 'git-apply'):
                    continue
                data = read_source(row[1], old)
                paths = ident._patch_targets_bytes(data)
                if paths is None:
                    raise ValueError('opaque patch targets: ' + row[1])
                def matches(path):
                    return path == package if global_file else path.startswith(package + '/')
                if not any(matches(path) for path in paths):
                    continue
                if row[0] == 'git-apply':
                    if any(not matches(path) for path in paths) or b'GIT binary patch' in data:
                        raise ValueError('git patch extends outside selected package')
                    subprocess.run([git, '-C', str(stage), 'apply', '--whitespace=nowarn', '-'], input=data, check=True)
                else:
                    sections = ident._update_patch_sections(data)
                    if sections is None:
                        raise ValueError('opaque unified patch: ' + row[1])
                    matching = []
                    for names, part in sections:
                        section_names = ([package] if global_file and
                                         names == [package + '.orig', package] else names)
                        if any(matches(name) for name in section_names):
                            if any(not matches(name) for name in section_names):
                                raise ValueError('patch section crosses selected package')
                            matching.append(part)
                    if matching:
                        subprocess.run([patch, '-f', '-E', '-d', str(stage), '-p1', '-F', '0', '-V', 'none', *patch_options],
                                       input=b''.join(matching), check=True, stdout=subprocess.DEVNULL,
                                       env=dict(os.environ, PATCH_VERSION_CONTROL='none'))
            for name, source in file_map(rows).items():
                if global_file or not name.startswith(package + '/'):
                    continue
                dest = exp.destination_parent(stage, name)
                if os.path.lexists(dest):
                    raise ValueError('exported file collision: ' + name)
                exp.ensure_destination_directory(stage, name.rpartition('/')[0])
                dest.write_bytes(read_source(source, old))
                source_mode = dirty_before.get(source, {}).get('mode') if old else None
                if source_mode is None and old:
                    source_mode = old_mode(source)
                if source_mode is None:
                    source_mode = stat.S_IMODE((ports / source).stat().st_mode)
                dest.chmod(source_mode & ~0o022)
            if not global_file:
                if old:
                    # A recorded export can contain a recipe defect which this
                    # update repairs. Retain structural checks and the exact
                    # live-preimage comparison below, but validate recipe
                    # completeness and checksums on the replacement.
                    exp.check_tree_links(stage, stage / package, package)
                else:
                    exp.check_recipe(stage / package, package, stage)
            return stage / package
        package_trees = []
        for index, package in enumerate(packages):
            overlay = overlays[package]
            old_pkg = prepare('old-' + str(index), old_records, True, package, overlay)
            new_pkg = prepare('new-' + str(index), new_records, False, package, overlay)
            live = exp.destination_parent(directory / 'pkgsrc', package)
            old_tree = inventory.snapshot_installed_tree(str(old_pkg)) if old_pkg is not None else {}
            new_tree = inventory.snapshot_installed_tree(str(new_pkg))
            if old_pkg is None and pending is None and os.path.lexists(live):
                raise ValueError('new package path already exists: ' + package)
            live_tree = inventory.snapshot_installed_tree(str(live)) if os.path.lexists(live) else {}
            if pending is None and old_tree != live_tree:
                raise ValueError('selected live package differs from the previous export')
            if pending is not None:
                for name in set(old_tree) | set(new_tree) | set(live_tree):
                    if live_tree.get(name) not in (old_tree.get(name), new_tree.get(name)):
                        raise ValueError('interrupted package differs from both recorded states: ' + name)
            if any(row['kind'] not in ('file', 'directory') for rows in (old_tree, new_tree)
                   for row in rows.values()):
                raise ValueError('selected package has unsupported links or special files')
            for name in set(old_tree) & set(new_tree):
                if old_tree[name]['kind'] != new_tree[name]['kind']:
                    raise ValueError('selected package entry changes type: ' + name)
            package_trees.append((package, new_pkg, old_tree, new_tree, live_tree))
        file_changes = []
        for name in selected_files:
            destination = exp.destination_parent(directory / 'pkgsrc', name)
            if name in global_files:
                old_path = prepare('old-file-' + str(len(file_changes)), old_records, True, name, None, global_file=True)
                new_path = prepare('new-file-' + str(len(file_changes)), new_records, False, name, None, global_file=True)
                if not old_path.is_file() or old_path.is_symlink() or not new_path.is_file() or new_path.is_symlink():
                    raise ValueError('patched global output is not a regular file: ' + name)
                before, after = old_path.read_bytes(), new_path.read_bytes()
                previous_mode = stat.S_IMODE(old_path.stat().st_mode)
                mode = stat.S_IMODE(new_path.stat().st_mode)
            else:
                before = read_source(old_files[name], True) if name in old_files else None
                after = read_source(new_files[name], False) if name in new_files else None
                old_source = old_files.get(name)
                previous_mode = old_mode(old_source) if old_source else None
                source = new_files.get(name)
                mode = (stat.S_IMODE((ports / source).stat().st_mode) & ~0o022) if source else None
            if os.path.lexists(destination):
                if destination.is_symlink() or not destination.is_file():
                    raise ValueError('selected live file has unsupported type: ' + name)
                actual = (destination.read_bytes(), stat.S_IMODE(destination.stat().st_mode))
                permitted = [(before, previous_mode)]
                if pending is not None:
                    permitted.append((after, mode))
                if actual not in permitted:
                    raise ValueError('selected live file differs: ' + name)
            elif before is not None and not (pending is not None and after is None):
                raise ValueError('selected live file is missing: ' + name)
            file_changes.append((destination, after, mode))
        input_names = set(snapshot['files'])
        for tree, rows in snapshot['trees'].items():
            input_names.update(tree + '/' + name for name, row in rows.items() if row['kind'] in ('file', 'link'))
        dirty = set(git_call('diff', '--name-only', 'HEAD', '--').stdout.decode().splitlines())
        dirty.update(git_call('ls-files', '--others', '--exclude-standard').stdout.decode().splitlines())
        dirty.update(git_call('ls-files', '--others', '-i', '--exclude-standard').stdout.decode().splitlines())
        dirty.update(current_refs - old_refs)
        dirty.update(ident.input_mode_overrides(ports, snapshot))
        dirty.update(tree + '/' + name for tree, rows in snapshot['trees'].items()
                     for name, row in rows.items() if row['kind'] == 'link')
        dirty_inputs, dirty_content = {}, {}
        for name in sorted(dirty & input_names):
            source = exp.source_path(ports, name, 'dirty export input')
            if not source.is_file():
                raise ValueError('dirty export input is not a regular file: ' + name)
            content = source.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            if sha != snapshot_hash(snapshot, name):
                raise ValueError('dirty export input changed while read: ' + name)
            # The exporter removes group/other write bits from copied inputs.
            mode = stat.S_IMODE(source.stat().st_mode) & ~0o022
            if not ident.valid_input_mode(mode):
                raise ValueError('unsupported dirty export input mode: ' + name)
            tracked, tracked_mode = historical_file(name, current['ports_commit'])
            if tracked == content and tracked_mode == mode:
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
                json.dump({'packages': packages, 'files': selected_files,
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
        for package, new_pkg, old_tree, new_tree, live_tree in package_trees:
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
        updated = {'format': ident.SHARED_EXPORT_FORMAT, 'version': ident.SHARED_EXPORT_VERSION, 'identity': current,
                   'material': {name: ident.material_snapshot(directory / 'pkgsrc' / name)
                                for name in ident.SHARED_EXPORT_MATERIAL}, 'inputs': snapshot,
                   'dirty_inputs': dirty_inputs}
        provenance = copy.deepcopy(receipt['patch_provenance'])
        for package in packages:
            for name in list(provenance['files']):
                if name.startswith(package + '/'):
                    del provenance['files'][name]
            if current['patch'] == provenance['base']:
                provenance['packages'].pop(package, None)
            else:
                provenance['packages'][package] = current['patch']
        for name in selected_files:
            parent = '/'.join(name.split('/')[:2])
            inherited = provenance['packages'].get(parent, provenance['base'])
            if current['patch'] == inherited:
                provenance['files'].pop(name, None)
            else:
                provenance['files'][name] = current['patch']
        ident.validate_patch_provenance(provenance)
        updated['patch_provenance'] = provenance
        # Commit the complete expected receipt to the durable marker first.
        # A resumed transaction accepts no other published receipt, even if
        # its input identity happens to match.
        pending_marker = {'packages': packages, 'files': selected_files,
                          'previous_receipt': receipt, 'new_identity': current,
                          'expected_new_receipt': updated}
        replace(marker, (json.dumps(pending_marker, sort_keys=True) + '\n').encode(), 0o600)
        replace(receipt_path, (json.dumps(updated, sort_keys=True) + '\n').encode(), 0o644)
        marker.unlink()
        sync_dir(directory)
        if cache.is_dir() and not cache.is_symlink():
            for blob in cache.iterdir():
                if blob.name not in dirty_content and blob.is_file() and not blob.is_symlink():
                    blob.unlink()
            sync_dir(cache)
        return updated
