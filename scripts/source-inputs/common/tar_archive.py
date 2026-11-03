#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Shared patched single-archive preparation and verification."""
import os
from pathlib import Path
import re
import sys
import tempfile

def verify(ctx, source, git, archive=None, patch=None, pkgsrc_export=None, export_patch=None):
    record = ctx.jsonio.read_json(str(Path(source) / ctx.sourceprep.PREPARED_TREE_RECEIPT))
    old = record.get('identity') if isinstance(record, dict) else None
    record = ctx.sourceprep.validate_prepared_tree(source, package=ctx.PACKAGE, identity=old)
    selector = ctx.identity_module()
    # An explicit export producer must be checked even on the Git fast path.
    shared = (selector.shared_export(pkgsrc_export, ctx.PORTS, git, ctx.SDK_SOURCE, export_patch)
              if pkgsrc_export and export_patch is not None else None)
    compatible = getattr(ctx, 'compatible_owner_digests', ())
    owner_digest = getattr(ctx, 'owner_digest', None)
    if isinstance(old, dict) and callable(owner_digest):
        expected_owner = old.get('owner_sha256') if old.get('owner_sha256') in compatible else owner_digest()
        if selector.current_git_package(
                old, expected_owner, lambda: ctx.git_effective_identity(git)):
            # The prepared tree is validated above and its package recipe,
            # patch set, and selected owner still match. Unrelated shared
            # export inputs are not consumed on this path.
            return record

    # Only compare the whole shared export on paths that need it to rebuild
    # or compare the selected package payload.
    if shared is None and pkgsrc_export:
        shared = selector.shared_export(pkgsrc_export, ctx.PORTS, git, ctx.SDK_SOURCE, patch)
    identity = ctx.source_identity(git)
    if old == identity:
        return record
    if (isinstance(old, dict) and old.get('owner_sha256') in compatible and
            set(old) == {'export', 'owner_sha256'} and old['export'] == identity['export']):
        return record
    if isinstance(old, dict) and set(old) == {'effective', 'owner_sha256'}:
        ctx.require(isinstance(old['owner_sha256'], str) and re.fullmatch('[0-9a-f]{64}', old['owner_sha256']),
                f'invalid scoped {ctx.LABEL} owner identity')
        expected_owner = old['owner_sha256'] if old['owner_sha256'] in compatible else identity['owner_sha256']
        if ctx.identity_module().current_git_package(old, expected_owner, lambda: ctx.git_effective_identity(git)):
            # The receipt names the Git objects of the current effective recipe.
            ctx.require(identity == ctx.source_identity(git), 'pkgsrc export inputs changed during verification')
            return record
        ctx.require(patch and os.path.isabs(patch), f'effective {ctx.LABEL} verification requires an explicit patch')
        with tempfile.TemporaryDirectory(prefix=f'.{ctx.LABEL}-verify-') as tmp:
            selector = ctx.identity_module()
            if pkgsrc_export:
                exported = shared
            else:
                exported = Path(tmp) / 'pkgsrc'
                ctx.process.capture([sys.executable, '-B', str(ctx.PORTS / 'scripts/prepare-pkgsrc.py'),
                                 str(exported), '--git', git, '--patch', patch],
                                env=ctx.process.sanitized_environment())
            current = selector.effective_package_identity(exported, ctx.PACKAGE, identity['export']['upstream'])
            ctx.require(identity == ctx.source_identity(git), 'pkgsrc export inputs changed during verification')
            ctx.require(selector.equivalent_effective_package(old['effective'], old['effective']) and
                    old['effective']['package'] == ctx.PACKAGE,
                    f'invalid scoped {ctx.LABEL} package identity')
            if (not selector.equivalent_effective_package(old['effective'], current) or
                    old['owner_sha256'] != identity['owner_sha256']):
                ctx.require(archive and os.path.isabs(archive),
                        f'changed {ctx.LABEL} inputs require an explicit archive for payload comparison')
                prepared = ctx.prepare(archive, Path(tmp) / 'expected', patch, git, exported=exported)
                ctx.require(identity == ctx.source_identity(git), 'pkgsrc export inputs changed during verification')
                ctx.require(prepared['tree_sha256'] == record['tree_sha256'],
                        f'prepared {ctx.LABEL} differs from current effective source')
        return record
    export = old.get('export') if isinstance(old, dict) else None
    ctx.require(isinstance(export, dict) and set(old) == {'export', 'owner_sha256'} and
            set(export) == {'api', 'package', 'export_inputs_sha256', 'upstream'} and
            type(export['api']) is int and export['api'] == 1 and export['package'] == ctx.PACKAGE and
            isinstance(export['export_inputs_sha256'], str) and re.fullmatch('[0-9a-f]{64}', export['export_inputs_sha256']) and
            isinstance(export['upstream'], str) and re.fullmatch('[0-9a-f]{40}', export['upstream']) and
            isinstance(old['owner_sha256'], str) and re.fullmatch('[0-9a-f]{64}', old['owner_sha256']),
            f'unrecognized legacy {ctx.LABEL} identity')
    ctx.require(archive and patch and os.path.isabs(archive) and os.path.isabs(patch),
            f'changed export requires an explicit archive and patch to compare {ctx.LABEL}')
    with tempfile.TemporaryDirectory(prefix=f'.{ctx.LABEL}-verify-') as tmp:
        expected = Path(tmp) / 'expected'
        exported = shared
        prepared = ctx.prepare(archive, expected, patch, git, exported=exported)
        ctx.require(identity == ctx.source_identity(git), 'pkgsrc export inputs changed during verification')
        ctx.require(prepared['tree_sha256'] == record['tree_sha256'],
                f'prepared {ctx.LABEL} differs from current effective source')
    return record


def prepare(ctx, archive, output, patch, git, scoped_identity=False, exported=None):
    ctx.require(os.path.isabs(git) and os.path.isabs(patch), 'select absolute Git and patch executables')
    output = Path(output)
    ctx.require(output.is_absolute(), 'prepared source output must be absolute')
    output = Path(ctx.paths.canonical_existing(output.parent), output.name)
    ctx.require(not os.path.lexists(output), 'prepared source output already exists')
    ctx.paths.reject_overlap(str(output), str(ctx.PORTS))
    identity = ctx.source_identity(git)
    with tempfile.TemporaryDirectory(prefix=f'.{ctx.LABEL}-source-', dir=output.parent) as tmp:
        tmp = Path(tmp)
        if exported is None:
            exported = tmp / 'pkgsrc'
            ctx.process.capture([sys.executable, '-B', str(ctx.PORTS / 'scripts/prepare-pkgsrc.py'),
                             str(exported), '--git', git, '--patch', patch],
                            env=ctx.process.sanitized_environment())
        metadata, patches = ctx.recipe(exported)
        archive = Path(ctx.paths.canonical_existing(archive))
        ctx.require(archive.name == metadata['archive'], f'{ctx.LABEL} archive filename differs from recipe')
        data = ctx.read(archive)
        hashes = ctx.sourceprep.archive_hashes(data)
        ctx.require(all(hashes[key] == metadata[key] for key in ('sha512', 'blake2s', 'size')),
                f'{ctx.LABEL} archive checksum differs from recipe')
        packed = tmp / archive.name
        packed.write_bytes(data)
        archive_root = metadata.get('archive_root', metadata['distname'])
        ctx.sourceprep.extract_archive(packed, tmp, archive_root, ctx.PACKAGE)
        root = tmp / archive_root
        for index, path in enumerate(patches):
            delta = ctx.read(path)
            ctx.require(ctx.digest(delta) == metadata['recipe']['patches/' + path.name], f'{ctx.LABEL} patch changed')
            ctx.sourceprep.apply_patch(patch, path, delta, root, f'{ctx.LABEL}',
                patch_args=('-p0', '-f', '-N', '-F0', '-V', 'none'),
                backup_directory=tmp / ('patch-backups-' + str(index)))
        ctx.require(not any(p.name.endswith(('.orig', '.rej')) for p in root.rglob('*')),
                f'{ctx.LABEL} patch left a backup or reject')
        ctx.require(identity == ctx.source_identity(git), 'pkgsrc export inputs changed during preparation')
        if scoped_identity:
            identity = {'effective': ctx.git_effective_identity(git),
                        'owner_sha256': identity['owner_sha256']}
        record = ctx.prepared_receipt.write(root, package=ctx.PACKAGE, identity=identity)
        ctx.require(ctx.sourceprep.archive_hashes(ctx.read(archive)) == hashes, f'{ctx.LABEL} archive changed during preparation')
        ctx.publish_directory_noreplace(root, output)
    return record


def shared_tree(ctx, selected):
    """Return the run's shared pkgsrc export, bound to current inputs, if any."""
    if not selected.pkgsrc_export:
        return None
    ctx.require(selected.patch and os.path.isabs(selected.patch), 'select an absolute patch executable')
    return ctx.identity_module().shared_export(selected.pkgsrc_export, ctx.PORTS, selected.git, ctx.SDK_SOURCE, getattr(selected, 'export_patch', None) or selected.patch)
