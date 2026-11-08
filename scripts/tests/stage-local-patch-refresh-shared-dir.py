#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise patch refresh when adjacent package recipes share patch ownership."""
import hashlib
import importlib.util
import io
import argparse
from pathlib import Path
import sys
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--patch', type=Path, required=True)
args = parser.parse_args()
parser_dir = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage_local_patch_refresh',
                                              parser_dir / 'stage-local-patch-refresh.py')
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)

sdk_source = args.sdk_source
if not sdk_source.is_absolute() or not args.patch.is_absolute():
    raise SystemExit('SDK source and patch tool must be absolute')
sys.path.insert(0, str(sdk_source / 'src'))
from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep

sdk = dict(paths=paths, jsonio=jsonio, archive_metadata=archive_metadata, sourceprep=sourceprep)

def distinfo(archive, patch_name, patch_data):
    raw = archive.read_bytes()
    return (f'$NetBSD$\n\nBLAKE2s ({archive.name}) = {hashlib.blake2s(raw).hexdigest()}\n'
            f'SHA512 ({archive.name}) = {hashlib.sha512(raw).hexdigest()}\n'
            f'Size ({archive.name}) = {len(raw)} bytes\n'
            f'SHA1 ({patch_name}) = {hashlib.sha1(patch_data).hexdigest()}\n').encode()

def expect_refusal(call, marker):
    try:
        call()
    except (ValueError, OSError) as exc:
        assert marker in str(exc), str(exc)
    else:
        raise AssertionError('unsafe or incomplete shared patch input accepted')

with tempfile.TemporaryDirectory(prefix='patch-refresh-shared-dir-') as temp:
    base = Path(temp).resolve()
    roots = [base / 'old' / 'pkgsrc', base / 'new' / 'pkgsrc']
    for root in roots:
        (root / 'graphics/mesa-generators').mkdir(parents=True)
        (root / 'graphics/MesaLib/patches').mkdir(parents=True)
        (root / 'graphics/mesa-generators/Makefile').write_text('include ../MesaLib/mesa-source.mk\n')
        (root / 'graphics/MesaLib/Makefile').write_text('# shared source owner\n')
    old_recipe, new_recipe = (root / 'graphics/mesa-generators' for root in roots)
    old_owner, new_owner = (root / 'graphics/MesaLib' for root in roots)
    archive = base / 'mesa-1.tar'
    with tarfile.open(archive, 'w') as tar:
        item = tarfile.TarInfo('mesa-1/configure.ac')
        item.size = 4
        item.mode = 0o644
        tar.addfile(item, io.BytesIO(b'A\nB\n'))
    old_patch = b'--- configure.ac\n+++ configure.ac\n@@ -1,2 +1,2 @@\n A\n-B\n+old\n'
    new_patch = b'--- configure.ac\n+++ configure.ac\n@@ -1,2 +1,2 @@\n A\n-B\n+new\n'
    patch_name = 'patch-src_configure.ac'
    (old_owner / 'patches' / patch_name).write_bytes(old_patch)
    (new_owner / 'patches' / patch_name).write_bytes(new_patch)
    old_info = distinfo(archive, patch_name, old_patch)
    (old_owner / 'distinfo').write_bytes(old_info)
    (new_owner / 'distinfo').write_bytes(distinfo(archive, patch_name, new_patch))
    work = base / 'work'
    source = work / 'mesa-1'
    source.mkdir(parents=True)
    (source / 'configure.ac').write_bytes(b'A\nold\n')
    old_patch_path = old_recipe / '../MesaLib/patches' / patch_name
    (work / '.patch_done').write_text(str(old_patch_path) + '\n')
    build_version = base / 'BUILD_VERSION'
    build_version.write_text(
        'graphics/mesa-generators/Makefile: ' + hashlib.sha256((old_recipe / 'Makefile').read_bytes()).hexdigest() + '\n' +
        'graphics/MesaLib/patches/' + patch_name + ': ' + hashlib.sha256(old_patch).hexdigest() + '\n')
    scratch = base / 'scratch'
    scratch.mkdir()
    result = refresh.prepare(
        sdk, new_recipe, work, archive, 'mesa-1', build_version,
        args.patch, ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'], scratch,
        previous_recipe=old_recipe, patchdir=new_owner / 'patches', distinfo=new_owner / 'distinfo',
        previous_patchdir=old_owner / 'patches', previous_distinfo=old_owner / 'distinfo')
    assert [(name, before, after) for name, before, after, _, _ in result[0]] == [
        ('configure.ac', b'A\nold\n', b'A\nnew\n')]
    assert refresh.selected_patch_inputs(roots[1], new_owner / 'patches', new_owner / 'distinfo') == (
        (new_owner / 'patches').resolve(), (new_owner / 'distinfo').resolve())
    # The package producer records the archive recipe's patch bytes, but not
    # the whole distinfo file. Its declared archive checksums and patch
    # inventory still authenticate the old replay.
    bad_patch_scratch = base / 'bad-patch-scratch'
    bad_patch_scratch.mkdir()
    saved_old_patch = (old_owner / 'patches' / patch_name).read_bytes()
    (old_owner / 'patches' / patch_name).write_bytes(saved_old_patch + b'# changed\n')
    expect_refusal(lambda: refresh.prepare(
        sdk, new_recipe, work, archive, 'mesa-1', build_version,
        args.patch, ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'], bad_patch_scratch,
        previous_recipe=old_recipe, patchdir=new_owner / 'patches', distinfo=new_owner / 'distinfo',
        previous_patchdir=old_owner / 'patches', previous_distinfo=old_owner / 'distinfo'),
        'old patch identity changed')
    (old_owner / 'patches' / patch_name).write_bytes(saved_old_patch)
    bad_archive_scratch = base / 'bad-archive-scratch'
    bad_archive_scratch.mkdir()
    saved_archive = archive.read_bytes()
    archive.write_bytes(saved_archive + b'changed')
    expect_refusal(lambda: refresh.prepare(
        sdk, new_recipe, work, archive, 'mesa-1', build_version,
        args.patch, ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'], bad_archive_scratch,
        previous_recipe=old_recipe, patchdir=new_owner / 'patches', distinfo=new_owner / 'distinfo',
        previous_patchdir=old_owner / 'patches', previous_distinfo=old_owner / 'distinfo'),
        'archive differs from previous distinfo')
    archive.write_bytes(saved_archive)
    outside = base / 'outside'
    (outside / 'patches').mkdir(parents=True)
    (outside / 'distinfo').write_text('')
    expect_refusal(lambda: refresh.selected_patch_inputs(roots[1], base / 'outside/patches',
                                                          base / 'outside/distinfo'),
                   'exported pkgsrc tree')
    (old_owner / 'patches' / 'patch-unrecorded').write_bytes(b'not part of installed inventory')
    bad_scratch = base / 'bad-scratch'
    bad_scratch.mkdir()
    expect_refusal(lambda: refresh.old_metadata(
        paths, new_recipe, work, build_version, previous_recipe=old_recipe,
        patchdir=new_owner / 'patches',
        previous_patchdir=old_owner / 'patches'),
        'inventory differs')

    # Additive refresh for a current recipe that shares an owner, without a
    # previous-recipe snapshot: old patch leaves remain in the shared owner.
    add_root = base / 'additive/pkgsrc'
    add_recipe = add_root / 'graphics/mesa-generators'
    add_owner = add_root / 'graphics/MesaLib'
    (add_recipe).mkdir(parents=True)
    (add_owner / 'patches').mkdir(parents=True)
    (add_recipe / 'Makefile').write_text('include ../MesaLib/mesa-source.mk\n')
    (add_owner / 'Makefile').write_text('# shared source owner\n')
    archive = base / 'additive-mesa-1.tar'
    with tarfile.open(archive, 'w') as tar:
        for path, data in [('mesa-1/configure.ac', b'A\nB\n'), ('mesa-1/extra.h', b'old\n')]:
            item = tarfile.TarInfo(path)
            item.size = len(data)
            item.mode = 0o644
            tar.addfile(item, io.BytesIO(data))
    first = b'--- configure.ac\n+++ configure.ac\n@@ -1,2 +1,2 @@\n A\n-B\n+old\n'
    second = b'--- extra.h\n+++ extra.h\n@@ -1 +1 @@\n-old\n+new\n'
    first_name, second_name = 'patch-a', 'patch-b'
    (add_owner / 'patches' / first_name).write_bytes(first)
    (add_owner / 'patches' / second_name).write_bytes(second)
    add_info = distinfo(archive, first_name, first) + f'SHA1 ({second_name}) = {hashlib.sha1(second).hexdigest()}\n'.encode()
    (add_owner / 'distinfo').write_bytes(add_info)
    add_work = base / 'add-work'
    add_source = add_work / 'mesa-1'
    add_source.mkdir(parents=True)
    (add_source / 'configure.ac').write_bytes(b'A\nold\n')
    (add_source / 'extra.h').write_bytes(b'old\n')
    old_cookie_path = (add_owner / 'patches' / first_name).resolve()
    (add_work / '.patch_done').write_text(str(old_cookie_path) + '\n')
    add_version = base / 'add-BUILD_VERSION'
    add_version.write_text(
        'graphics/mesa-generators/Makefile: ' + hashlib.sha256((add_recipe / 'Makefile').read_bytes()).hexdigest() + '\n' +
        'graphics/MesaLib/patches/' + first_name + ': ' + hashlib.sha256(first).hexdigest() + '\n')
    saved_add_cookie = (add_work / '.patch_done').read_bytes()
    (add_work / '.patch_done').write_bytes(b'')
    expect_refusal(lambda: refresh.old_metadata(
        paths, add_recipe, add_work, add_version, patchdir=add_owner / 'patches'),
        'empty patch cookie contradicts installed patch provenance')
    (add_work / '.patch_done').write_bytes(saved_add_cookie)
    add_scratch = base / 'add-scratch'
    add_scratch.mkdir()
    added = refresh.prepare(
        sdk, add_recipe, add_work, archive, 'mesa-1', add_version,
        args.patch, ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'], add_scratch,
        patchdir=add_owner / 'patches', distinfo=add_owner / 'distinfo')
    assert [(name, before, after) for name, before, after, _, _ in added[0]] == [
        ('extra.h', b'old\n', b'new\n')]
print('PASS shared patch owner replay, containment, and full old inventory')
