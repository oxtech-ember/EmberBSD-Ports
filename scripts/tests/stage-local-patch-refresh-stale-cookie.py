#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Reconcile an old inventory only when complete installed preimages match."""
import argparse
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True, type=Path)
parser.add_argument('--patch', required=True, type=Path)
args = parser.parse_args()
sys.path.insert(0, str(args.sdk_source / 'src'))
from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep
helper = Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py'
spec = importlib.util.spec_from_file_location('refresh', helper)
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)
sdk = dict(paths=paths, jsonio=jsonio, archive_metadata=archive_metadata, sourceprep=sourceprep)

with tempfile.TemporaryDirectory(prefix='refresh-stale-cookie-') as directory:
    root = Path(directory).resolve()
    recipe, previous = root / 'pkgsrc/cat/demo', root / 'previous'
    work = root / 'work'
    source = work / 'demo-1'
    source.mkdir(parents=True)
    archive = root / 'demo-1.tar.xz'
    with tarfile.open(archive, 'w:xz') as tar:
        for leaf in ('changing', 'reconciled'):
            member = tarfile.TarInfo('demo-1/' + leaf)
            member.size = 5
            member.mode = 0o644
            tar.addfile(member, io.BytesIO(b'base\n'))
    raw = archive.read_bytes()
    archive_info = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(raw).hexdigest()}\n'
                    f'SHA512 ({archive.name}) = {hashlib.sha512(raw).hexdigest()}\n'
                    f'Size ({archive.name}) = {len(raw)} bytes\n')
    for folder, value in ((previous, 'old'), (recipe, 'new')):
        (folder / 'patches').mkdir(parents=True)
        (folder / 'Makefile').write_text('# fixture\n')
        rows = archive_info
        for name, leaf, result in (('patch-a', 'changing', value), ('patch-b', 'reconciled', 'present')):
            data = f'--- {leaf}\n+++ {leaf}\n@@ -1 +1 @@\n-base\n+{result}\n'.encode()
            (folder / 'patches' / name).write_bytes(data)
            rows += f'SHA1 ({name}) = {hashlib.sha1(data).hexdigest()}\n'
        (folder / 'distinfo').write_text(rows)
    version = root / 'BUILD_VERSION'
    inputs = ('Makefile', 'distinfo', 'patches/patch-a', 'patches/patch-b')
    version.write_text(''.join(f'cat/demo/{name}: {hashlib.sha256((previous / name).read_bytes()).hexdigest()}\n'
                               for name in inputs))
    cookie = (str(recipe / 'patches/patch-a') + '\n').encode()
    (work / '.patch_done').write_bytes(cookie)
    for leaf, value in (('changing', b'old\n'), ('reconciled', b'present\n'), ('compatible.o', b'object\n')):
        (source / leaf).write_bytes(value)
        (source / leaf).chmod(0o644)
    patch_args = ['-E', '-p0', '--batch', '--forward', '-V', 'simple', '-z', '.orig']
    def prepare(name, old_cookie=None):
        scratch = root / name
        scratch.mkdir()
        return refresh.prepare(sdk, recipe, work, archive, 'demo-1', version,
                               args.patch, patch_args, scratch, previous_recipe=previous,
                               old_cookie=old_cookie)
    changes, old_cookie, names = prepare('first')
    assert old_cookie == cookie and names == ['patch-a', 'patch-b']
    assert changes[1][:3] == ('reconciled', b'present\n', b'present\n')
    inventory = [recipe / 'patches' / name for name in names]

    # Stale metadata must never authorize applying the omitted patch itself.
    (source / 'reconciled').write_bytes(b'base\n')
    try:
        refresh.transaction(sdk, work, source, changes, cookie, inventory, lambda: None)
    except ValueError as exc:
        assert 'preimage differs' in str(exc)
    else:
        raise AssertionError('unapplied omitted patch accepted')
    assert (source / 'changing').read_bytes() == b'old\n'
    assert (work / '.patch_done').read_bytes() == cookie
    (source / 'reconciled').write_bytes(b'present\n')
    retained = {name: (source / name).stat().st_mtime_ns for name in ('reconciled', 'compatible.o')}
    def interrupted_clean():
        raise RuntimeError('clean interrupted')
    try:
        refresh.transaction(sdk, work, source, changes, cookie, inventory, interrupted_clean)
    except RuntimeError:
        pass
    else:
        raise AssertionError('clean interruption ignored')
    prior = refresh.journal_old_cookie(sdk, work)
    retried, prior, names = prepare('retry', old_cookie=prior)
    refresh.transaction(sdk, work, source, retried, prior, inventory, lambda: None)
    assert (source / 'changing').read_bytes() == b'new\n'
    assert (work / '.patch_done').read_bytes() == ''.join(str(path) + '\n' for path in inventory).encode()
    assert all((source / name).stat().st_mtime_ns == timestamp for name, timestamp in retained.items())
    assert not (work / '.emberbsd-patch-refresh.json').exists()

    # A supplied snapshot cannot silently omit installed patch provenance.
    (previous / 'patches/patch-b').unlink()
    try:
        prepare('missing-snapshot-patch', old_cookie=cookie)
    except ValueError as exc:
        assert 'inventory differs from installed provenance' in str(exc)
    else:
        raise AssertionError('incomplete previous recipe accepted')

print('PASS: stale cookie requires complete installed preimages, preserves mtimes and recovers forward')
