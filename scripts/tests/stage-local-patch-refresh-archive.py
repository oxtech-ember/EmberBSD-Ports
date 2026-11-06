#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check bounded archive links and patch endpoints before patch execution."""
import argparse
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--patch', type=Path, required=True)
args = parser.parse_args()
if not args.sdk_source.is_absolute() or not args.patch.is_absolute() or not args.patch.is_file():
    parser.error('select absolute SDK source and patch tool paths')
sys.path.insert(0, str(args.sdk_source / 'src'))
from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep
from emberbsd_sdk.errors import SDKError

helper = Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py'
spec = importlib.util.spec_from_file_location('stage_local_patch_refresh', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def exercise(root, mode):
    recipe = root / 'pkgsrc/cat/demo'
    patchdir = recipe / 'patches'
    patchdir.mkdir(parents=True)
    work = root / 'work'
    work.mkdir()
    live = work / 'demo-1'
    (live / 'real').mkdir(parents=True)
    (live / 'real/file').write_bytes(b'old\n')
    archive = root / 'demo-1.tar'
    target = 'real/file' if mode in ('valid', 'backup', 'size') else 'alias/file' if mode == 'ancestor' else 'alias'
    patch = ('--- ' + target + '\n+++ ' + target + '\n@@ -1 +1 @@\n-old\n+new\n').encode()
    (patchdir / 'patch-a').write_bytes(patch)
    (recipe / 'Makefile').write_text('# fixture\n')
    with tarfile.open(archive, 'w') as tar:
        entry = tarfile.TarInfo('demo-1/real/file')
        entry.size = 4
        tar.addfile(entry, io.BytesIO(b'old\n'))
        link = tarfile.TarInfo('demo-1/' + ('real/file.orig' if mode == 'backup' else 'alias'))
        link.type = tarfile.SYMTYPE
        link.linkname = 'file' if mode == 'backup' else 'real' if mode == 'ancestor' else 'real/file'
        tar.addfile(link)
    raw = archive.read_bytes()
    base = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(raw).hexdigest()}\n'
            f'SHA512 ({archive.name}) = {hashlib.sha512(raw).hexdigest()}\n'
            f'Size ({archive.name}) = {len(raw)} bytes\n')
    old_info = ('$NetBSD$\n\n' + base).encode()
    (recipe / 'distinfo').write_bytes(old_info + f'SHA1 (patch-a) = {hashlib.sha1(patch).hexdigest()}\n'.encode())
    (work / '.patch_done').write_bytes(b'')
    version = root / 'BUILD_VERSION'
    version.write_text('cat/demo/distinfo: ' + hashlib.sha256(old_info).hexdigest() + '\n')
    calls = []
    def apply(*positional, **keyword):
        calls.append(1)
        return sourceprep.apply_patch(*positional, **keyword)
    proxy = SimpleNamespace(ARCHIVE_INTERNAL_SYMLINKS_API=sourceprep.ARCHIVE_INTERNAL_SYMLINKS_API,
                            archive_hashes=sourceprep.archive_hashes,
                            extract_archive=sourceprep.extract_archive, apply_patch=apply)
    sdk = dict(paths=paths, sourceprep=proxy, archive_metadata=archive_metadata, jsonio=jsonio)
    scratch = root / 'scratch'
    scratch.mkdir()
    if mode == 'size':
        module.MAX_STAGE_ARCHIVE_BYTES = 3
    try:
        result = module.prepare(sdk, recipe, work, archive, 'demo-1', version,
                                args.patch, ['-E', '-p0', '--batch', '--forward',
                                             '-V', 'simple', '-z', '.orig'], scratch)
    except (ValueError, SDKError) as exc:
        if mode == 'valid':
            raise
        if calls:
            raise AssertionError(mode + ': patch invoked before refusal') from exc
        expected = 'extraction size limit' if mode == 'size' else 'real directory' if mode == 'ancestor' else 'regular file'
        if expected not in str(exc):
            raise AssertionError(mode + ': wrong refusal: ' + str(exc)) from exc
    else:
        if mode != 'valid' or len(calls) != 1 or result[0][0][1:3] != (b'old\n', b'new\n'):
            raise AssertionError(mode + ': unexpected successful replay')
    finally:
        module.MAX_STAGE_ARCHIVE_BYTES = 512 * 1024 * 1024
    print('PASS', mode)


with tempfile.TemporaryDirectory(prefix='patch-refresh-archive-') as tmp:
    for case in ('valid', 'ancestor', 'leaf', 'backup', 'size'):
        case_root = Path(tmp) / case
        case_root.mkdir()
        exercise(case_root, case)
