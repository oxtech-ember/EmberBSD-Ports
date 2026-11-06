#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify replacement of a provenance-bound existing patch."""
import argparse
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--patch', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.sdk_source / 'src'))
from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep
spec = importlib.util.spec_from_file_location('refresh', Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sdk = dict(paths=paths, jsonio=jsonio, archive_metadata=archive_metadata, sourceprep=sourceprep)
with tempfile.TemporaryDirectory(prefix='changed-patch-test-') as temp:
    root = Path(temp)
    recipe = root / 'pkgsrc/cat/demo'
    previous = root / 'previous'
    for directory in (recipe / 'patches', previous / 'patches'):
        directory.mkdir(parents=True)
    work = root / 'work'
    source = work / 'demo-1'
    source.mkdir(parents=True)
    archive = root / 'demo-1.tar.xz'
    with tarfile.open(archive, 'w:xz') as tar:
        for name, data in [('demo-1/input', b'base\n'), ('demo-1/sibling', b'keep\n')]:
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o644
            tar.addfile(item, io.BytesIO(data))
    old_patch = b'--- input\n+++ input\n@@ -1 +1 @@\n-base\n+old\n'
    new_patch = b'--- input\n+++ input\n@@ -1 +1 @@\n-base\n+new\n'
    data = archive.read_bytes()
    rows = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(data).hexdigest()}\n'
            f'SHA512 ({archive.name}) = {hashlib.sha512(data).hexdigest()}\n'
            f'Size ({archive.name}) = {len(data)} bytes\n')
    for directory, patch in ((previous, old_patch), (recipe, new_patch)):
        (directory / 'Makefile').write_text('# demo\n')
        (directory / 'patches/patch-a').write_bytes(patch)
        (directory / 'distinfo').write_text(rows + f'SHA1 (patch-a) = {hashlib.sha1(patch).hexdigest()}\n')
    (work / '.patch_done').write_text(str(previous / 'patches/patch-a') + '\n')
    (source / 'input').write_bytes(b'old\n')
    (source / 'sibling').write_bytes(b'keep\n')
    (source / 'object.o').write_bytes(b'object\n')
    version = root / 'BUILD_VERSION'
    version.write_text(''.join(f'cat/demo/{name}: {hashlib.sha256((previous / name).read_bytes()).hexdigest()}\n'
                               for name in ('Makefile', 'distinfo', 'patches/patch-a')))
    patchargs = ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig']
    def replay(name):
        scratch = root / name
        scratch.mkdir()
        return module.prepare(sdk, recipe, work, archive, 'demo-1', version, args.patch, patchargs,
                              scratch, previous_recipe=previous)
    changes, cookie, inventory = replay('ok')
    assert [(n, old, new) for n, old, new, _, _ in changes] == [('input', b'old\n', b'new\n')]
    sibling = (source / 'sibling').stat().st_mtime_ns
    obj = (source / 'object.o').stat().st_mtime_ns
    (source / 'input').write_bytes(b'foreign\n')
    try:
        module.transaction(sdk, work, source, changes, cookie, [recipe / 'patches' / n for n in inventory], lambda: None)
    except ValueError as exc:
        assert 'preimage differs' in str(exc)
    else:
        raise AssertionError('foreign live source accepted')
    (source / 'input').write_bytes(b'old\n')
    module.transaction(sdk, work, source, changes, cookie, [recipe / 'patches' / n for n in inventory], lambda: None)
    assert (source / 'input').read_bytes() == b'new\n'
    assert (source / 'sibling').stat().st_mtime_ns == sibling
    assert (source / 'object.o').stat().st_mtime_ns == obj
    saved_cookie = (work / '.patch_done').read_bytes()
    unknown = root / 'unknown/patches'
    unknown.mkdir(parents=True)
    (unknown / 'patch-a').write_bytes(old_patch)
    alias = root / 'previous-alias'
    alias.symlink_to(previous, target_is_directory=True)
    for name, origin in [('unknown-origin', unknown / 'patch-a'),
                         ('symlink-origin', alias / 'patches/patch-a')]:
        (work / '.patch_done').write_text(str(origin) + '\n')
        try:
            replay(name)
        except ValueError as exc:
            assert 'unsupported path' in str(exc)
        else:
            raise AssertionError('foreign or aliased patch cookie accepted')
    (work / '.patch_done').write_bytes(saved_cookie)
    (previous / 'patches/patch-a').write_bytes(b'foreign\n')
    try:
        replay('bad-old')
    except ValueError as exc:
        assert 'old patch identity changed' in str(exc)
    else:
        raise AssertionError('foreign old patch accepted')
    (previous / 'patches/patch-a').write_bytes(old_patch)
    archive.write_bytes(data + b'foreign')
    try:
        replay('bad-archive')
    except ValueError as exc:
        assert 'archive differs' in str(exc)
    else:
        raise AssertionError('foreign archive accepted')
print('PASS: changed patch replay, provenance, preimage and timestamps')
