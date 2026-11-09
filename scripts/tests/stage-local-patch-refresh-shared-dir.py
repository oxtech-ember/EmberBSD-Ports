#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise patch refresh when adjacent package recipes share patch ownership."""
import hashlib
import importlib.util
import io
import argparse
import os
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
from emberbsd_sdk.errors import SDKError

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
    except (ValueError, OSError, SDKError) as exc:
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
        for path, data in [('mesa-1/configure.ac', b'A\nB\n'),
                           ('mesa-1/extra.h', b'base\n'), ('mesa-1/keep.h', b'base\n')]:
            item = tarfile.TarInfo(path)
            item.size = len(data)
            item.mode = 0o644
            tar.addfile(item, io.BytesIO(data))
    old_patch = b'--- configure.ac\n+++ configure.ac\n@@ -1,2 +1,2 @@\n A\n-B\n+old\n'
    new_patch = b'--- configure.ac\n+++ configure.ac\n@@ -1,2 +1,2 @@\n A\n-B\n+new\n'
    patch_name = 'patch-src_configure.ac'
    extra_patch = b'--- extra.h\n+++ extra.h\n@@ -1 +1 @@\n-base\n+patched\n'
    extra_name = 'patch-src_extra.h'
    keep_patch = b'--- keep.h\n+++ keep.h\n@@ -1 +1 @@\n-base\n+patched\n'
    keep_name = 'patch-src_keep.h'
    (old_owner / 'patches' / patch_name).write_bytes(old_patch)
    (old_owner / 'patches' / extra_name).write_bytes(extra_patch)
    (old_owner / 'patches' / keep_name).write_bytes(keep_patch)
    (new_owner / 'patches' / patch_name).write_bytes(new_patch)
    (new_owner / 'patches' / extra_name).write_bytes(extra_patch)
    (new_owner / 'patches' / keep_name).write_bytes(keep_patch)
    old_info = distinfo(archive, patch_name, old_patch) + (
        f'SHA1 ({extra_name}) = {hashlib.sha1(extra_patch).hexdigest()}\n'.encode() +
        f'SHA1 ({keep_name}) = {hashlib.sha1(keep_patch).hexdigest()}\n'.encode())
    (old_owner / 'distinfo').write_bytes(old_info)
    (new_owner / 'distinfo').write_bytes(distinfo(archive, patch_name, new_patch) +
        f'SHA1 ({extra_name}) = {hashlib.sha1(extra_patch).hexdigest()}\n'.encode() +
        f'SHA1 ({keep_name}) = {hashlib.sha1(keep_patch).hexdigest()}\n'.encode())
    work = base / 'work'
    source = work / 'mesa-1'
    source.mkdir(parents=True)
    (source / 'configure.ac').write_bytes(b'A\nold\n')
    (source / 'extra.h').write_bytes(b'patched\n')
    (source / 'keep.h').write_bytes(b'patched\n')
    (source / 'keep.txt').write_bytes(b'untouched\n')
    os.utime(source / 'keep.txt', ns=(1_000_000_000, 1_000_000_000))
    old_patch_path = old_recipe / '../MesaLib/patches' / patch_name
    old_extra_path = old_recipe / '../MesaLib/patches' / extra_name
    old_keep_path = old_recipe / '../MesaLib/patches' / keep_name
    full_cookie = ''.join(str(path) + '\n' for path in
                          (old_patch_path, old_extra_path, old_keep_path)).encode()
    (work / '.patch_done').write_bytes(full_cookie)
    build_version = base / 'BUILD_VERSION'
    build_version.write_text(
        'graphics/mesa-generators/Makefile: ' + hashlib.sha256((old_recipe / 'Makefile').read_bytes()).hexdigest() + '\n' +
        'graphics/MesaLib/patches/' + patch_name + ': ' + hashlib.sha256(old_patch).hexdigest() + '\n' +
        'graphics/MesaLib/patches/' + extra_name + ': ' + hashlib.sha256(extra_patch).hexdigest() + '\n' +
        'graphics/MesaLib/patches/' + keep_name + ': ' + hashlib.sha256(keep_patch).hexdigest() + '\n')
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
    reversed_cookie = (str(old_owner / 'patches' / keep_name) + '\n' +
                       str(old_owner / 'patches' / extra_name) + '\n' +
                       str(old_owner / 'patches' / patch_name) + '\n').encode()
    (work / '.patch_done').write_bytes(reversed_cookie)
    expect_refusal(lambda: refresh.old_metadata(
        paths, new_recipe, work, build_version, previous_recipe=old_recipe,
        patchdir=new_owner / 'patches', previous_patchdir=old_owner / 'patches'),
        'old patch cookie is not an ordered subsequence')
    foreign_patch = base / 'foreign/patches/patch-unknown'
    foreign_patch.parent.mkdir(parents=True)
    foreign_patch.write_text('foreign')
    (work / '.patch_done').write_text(str(foreign_patch) + '\n')
    expect_refusal(lambda: refresh.old_metadata(
        paths, new_recipe, work, build_version, previous_recipe=old_recipe,
        patchdir=new_owner / 'patches', previous_patchdir=old_owner / 'patches'),
        'old patch cookie contains an unsupported path')
    (work / '.patch_done').write_bytes(full_cookie)
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
    # Explicit failed-stage recovery replays exactly the applied cookie, then
    # applies the complete current inventory to the reconstructed source.
    (source / 'extra.h').write_bytes(b'base\n')
    partial_cookie = ''.join(str(path) + '\n' for path in (old_patch_path, old_keep_path)).encode()
    (work / '.patch_done').write_bytes(partial_cookie)
    stale_scratch = base / 'stale-cookie-scratch'
    stale_scratch.mkdir()
    stale = refresh.prepare(
        sdk, new_recipe, work, archive, 'mesa-1', build_version,
        args.patch, ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'], stale_scratch,
        previous_recipe=old_recipe, patchdir=new_owner / 'patches', distinfo=new_owner / 'distinfo',
        previous_patchdir=old_owner / 'patches', previous_distinfo=old_owner / 'distinfo')
    expect_refusal(lambda: refresh.transaction(
        sdk, work, source, stale[0], partial_cookie,
        [new_owner / 'patches' / name for name in stale[2]], lambda: None),
        'live preimage differs: extra.h')
    assert (source / 'configure.ac').read_bytes() == b'A\nold\n'
    assert (source / 'extra.h').read_bytes() == b'base\n'
    assert (source / 'keep.h').read_bytes() == b'patched\n'
    assert (work / '.patch_done').read_bytes() == partial_cookie
    assert not (work / '.emberbsd-patch-refresh.json').exists()
    recovery_scratch = base / 'recovery-scratch'
    recovery_scratch.mkdir()
    recovered = refresh.prepare(
        sdk, new_recipe, work, archive, 'mesa-1', build_version,
        args.patch, ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'], recovery_scratch,
        previous_recipe=old_recipe, patchdir=new_owner / 'patches', distinfo=new_owner / 'distinfo',
        previous_patchdir=old_owner / 'patches', previous_distinfo=old_owner / 'distinfo',
        recover_applied_patches=True)
    assert [(name, before, after) for name, before, after, _, _ in recovered[0]] == [
        ('configure.ac', b'A\nold\n', b'A\nnew\n'), ('extra.h', b'base\n', b'patched\n'),
        ('keep.h', b'patched\n', b'patched\n')]
    wrong = source / 'keep.h'
    wrong.write_bytes(b'foreign\n')
    os.utime(wrong, ns=(2_000_000_000, 2_000_000_000))
    wrong_mtime = wrong.stat().st_mtime_ns
    expect_refusal(lambda: refresh.transaction(
        sdk, work, source, recovered[0], partial_cookie,
        [new_owner / 'patches' / name for name in recovered[2]], lambda: None),
        'live preimage differs: keep.h')
    assert (source / 'configure.ac').read_bytes() == b'A\nold\n'
    assert (source / 'extra.h').read_bytes() == b'base\n'
    assert wrong.read_bytes() == b'foreign\n' and wrong.stat().st_mtime_ns == wrong_mtime
    assert (work / '.patch_done').read_bytes() == partial_cookie
    assert not (work / '.emberbsd-patch-refresh.json').exists()
    wrong.write_bytes(b'patched\n')
    os.utime(wrong, ns=(2_000_000_000, 2_000_000_000))
    keep_mtime = (source / 'keep.txt').stat().st_mtime_ns
    refresh.transaction(sdk, work, source, recovered[0], partial_cookie,
                        [new_owner / 'patches' / name for name in recovered[2]], lambda: None)
    assert (source / 'configure.ac').read_bytes() == b'A\nnew\n'
    assert (source / 'extra.h').read_bytes() == b'patched\n'
    assert (source / 'keep.h').read_bytes() == b'patched\n'
    assert (source / 'keep.h').stat().st_mtime_ns == wrong_mtime
    assert (source / 'keep.txt').stat().st_mtime_ns == keep_mtime
    assert (work / '.patch_done').read_text() == ''.join(str(new_owner / 'patches' / name) + '\n'
                                                          for name in recovered[2])
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

    # First patch for a package whose old recipe never had a patches directory.
    first_old = base / 'first-old/pkgsrc/devel/demo'
    first_new = base / 'first-new/pkgsrc/devel/demo'
    first_old.mkdir(parents=True)
    (first_new / 'patches').mkdir(parents=True)
    for owner in (first_old, first_new):
        (owner / 'Makefile').write_text('# no build fixture\n')
    first_info = b'\n'.join(line for line in add_info.split(b'\n')
                            if not line.startswith(b'SHA1 (patch-'))
    (first_old / 'distinfo').write_bytes(first_info)
    (first_new / 'distinfo').write_bytes(first_info +
        f'SHA1 ({first_name}) = {hashlib.sha1(first).hexdigest()}\n'.encode())
    (first_new / 'patches' / first_name).write_bytes(first)
    empty = refresh.selected_patch_inputs(first_old.parents[1], first_old / 'patches',
                                           first_old / 'distinfo')
    assert empty == (first_old / 'patches', first_old / 'distinfo')
    first_work = base / 'first-work'
    first_source = first_work / 'mesa-1'
    first_source.mkdir(parents=True)
    (first_source / 'configure.ac').write_bytes(b'A\nB\n')
    (first_source / 'keep.o').write_bytes(b'compatible object\n')
    retained = (first_source / 'keep.o').stat()
    (first_work / '.patch_done').write_bytes(b'')
    first_version = base / 'first-BUILD_VERSION'
    first_version.write_text('devel/demo/Makefile: ' +
                             hashlib.sha256((first_old / 'Makefile').read_bytes()).hexdigest() + '\n')
    def first_prepare(suffix):
        scratch = base / suffix
        scratch.mkdir()
        return refresh.prepare(sdk, first_new, first_work, archive, 'mesa-1', first_version,
            args.patch, ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig'],
            scratch, previous_recipe=first_old)
    first_result = first_prepare('first-scratch')
    refresh.transaction(sdk, first_work, first_source, first_result[0], b'',
                        [first_new / 'patches' / name for name in first_result[2]], lambda: None)
    assert (first_source / 'configure.ac').read_bytes() == b'A\nold\n'
    assert not (first_old / 'patches').exists()
    assert (first_source / 'keep.o').read_bytes() == b'compatible object\n'
    assert (first_source / 'keep.o').stat().st_ino == retained.st_ino
    assert (first_source / 'keep.o').stat().st_mtime_ns == retained.st_mtime_ns
    (first_work / '.patch_done').write_bytes(b'')
    (first_old / 'distinfo').write_bytes(first_info +
        f'SHA1 ({first_name}) = {hashlib.sha1(first).hexdigest()}\n'.encode())
    expect_refusal(lambda: first_prepare('first-missing-declared'), 'patch inventory differs')
    (first_old / 'patches').symlink_to(base / 'missing-patch-target')
    expect_refusal(lambda: refresh.selected_patch_inputs(first_old.parents[1],
                   first_old / 'patches', first_old / 'distinfo'), 'symlink alias')
    (first_old / 'patches').unlink()
    (first_old / 'patches').write_bytes(b'not a directory')
    expect_refusal(lambda: refresh.selected_patch_inputs(first_old.parents[1],
                   first_old / 'patches', first_old / 'distinfo'), 'not a directory')
print('PASS shared patch owner replay, containment, and full old inventory')
