#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise V8 producer reuse through the real SDK with a tiny source fixture."""
import argparse
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'git', 'patch', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
ports = Path(__file__).resolve().parents[3]


def run(*command, success=True):
    result = subprocess.run([str(x) for x in command], capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise AssertionError(f'{command!r}: {result.stdout}\n{result.stderr}')
    return result


with tempfile.TemporaryDirectory(prefix='v8-reuse-fixture-', dir=args.work_dir) as directory:
    work = Path(directory)
    root = work / 'ports'
    upstream = root / 'upstream/pkgsrc'
    upstream.mkdir(parents=True)
    (upstream / 'README').write_text('fixture upstream\n')
    run(args.git, '-C', upstream, 'init', '-q')
    run(args.git, '-C', upstream, 'add', 'README')
    run(args.git, '-C', upstream, '-c', 'user.name=Fixture', '-c',
        'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
    pin = run(args.git, '-C', upstream, 'rev-parse', 'HEAD').stdout.strip()
    for name in ('scripts/prepare-pkgsrc.py', 'scripts/pkgsrc-source-identity.py',
                 'scripts/prepared_receipt.py', 'scripts/source-inputs/v8/source.py',
                 'pkgsrc/lang/llvm/files/sdk_source.py'):
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ports / name, destination)
    package = root / 'pkgsrc/lang/v8'
    (package / 'patches').mkdir(parents=True)
    (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME= llvm-fixture\n')
    (root / 'pkgsrc/export.conf').write_text('file\tscripts/pkgsrc-source-identity.py\tEMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py\n')
    (root / 'pkgsrc/replaces').write_text('# fixture\n')
    run(args.git, '-C', root, 'init', '-q')
    run(args.git, '-C', root, 'add', 'pkgsrc/export.conf')
    run(args.git, '-C', root, 'update-index', '--add', '--cacheinfo',
        f'160000,{pin},upstream/pkgsrc')
    revision = 'a' * 40
    archive = work / f'v8-1.2.3.4-{revision}.tar.gz'
    version = ''.join(f'#define {macro} {value}\n' for macro, value in zip(
        ('V8_MAJOR_VERSION', 'V8_MINOR_VERSION', 'V8_BUILD_NUMBER', 'V8_PATCH_LEVEL'),
        (1, 2, 3, 4)))
    with tarfile.open(archive, 'w:gz') as tar:
        for name, data in [('include/v8-version.h', version),
                           ('include/v8config.h', 'original header\n'),
                           ('BUILD.gn', 'original gn\n')]:
            payload = data.encode()
            info = tarfile.TarInfo(f'v8-{revision}/{name}')
            info.size, info.mode, info.mtime = len(payload), 0o644, 1000000000
            tar.addfile(info, io.BytesIO(payload))
    archive_data = archive.read_bytes()
    header_patch = '--- include/v8config.h\n+++ include/v8config.h\n@@ -1 +1 @@\n-original header\n+patched header\n'
    gn_patch = lambda value: '--- BUILD.gn\n+++ BUILD.gn\n@@ -1 +1 @@\n-original gn\n+' + value + '\n'

    def recipe(gn_value, revision_number):
        (package / 'Makefile').write_text(f'V8_REVISION= {revision}\nV8_VERSION= 1.2.3.4\nPKGREVISION= {revision_number}\n')
        patches = {'patch-BUILD.gn': gn_patch(gn_value), 'patch-header': header_patch}
        for name, contents in patches.items():
            (package / 'patches' / name).write_text(contents)
        lines = [f'BLAKE2s ({archive.name}) = {hashlib.blake2s(archive_data).hexdigest()}',
                 f'SHA512 ({archive.name}) = {hashlib.sha512(archive_data).hexdigest()}',
                 f'Size ({archive.name}) = {len(archive_data)} bytes']
        lines.extend(f'SHA1 ({name}) = {hashlib.sha1(text.encode()).hexdigest()}'
                     for name, text in sorted(patches.items()))
        (package / 'distinfo').write_text('\n'.join(lines) + '\n')

    owner = root / 'scripts/source-inputs/v8/source.py'
    command = [sys.executable, '-B', '-I', '-S', owner, '--sdk-source', args.sdk_source,
               '--git', args.git, 'prepare', '--archive', archive, '--patch', args.patch]
    old, new = work / 'old', work / 'new'
    recipe('gn one', 1)
    run(*command, '--output', old)
    fixed_ns = 1100000000000000000
    for name in ('include/v8config.h', 'BUILD.gn'):
        os.utime(old / name, ns=(fixed_ns, fixed_ns))
    recipe('gn two', 2)
    run(*command, '--output', new, '--previous-source', old)
    assert (old / 'include/v8config.h').read_bytes() == (new / 'include/v8config.h').read_bytes()
    assert (new / 'include/v8config.h').stat().st_mtime_ns == fixed_ns
    assert (old / 'BUILD.gn').read_bytes() != (new / 'BUILD.gn').read_bytes()
    assert (new / 'BUILD.gn').stat().st_mtime_ns != fixed_ns
    assert (old / 'include/v8config.h').stat().st_mtime_ns == fixed_ns
    previous_entries = sorted(p.name for p in old.iterdir())
    previous_directory_mtime = old.stat().st_mtime_ns
    relative_output = work / 'relative-rejected'
    assert 'previous source must be absolute' in run(
        *command, '--output', relative_output, '--previous-source', 'old', success=False).stderr
    assert not relative_output.exists()
    nested_output = old / 'nested-rejected'
    assert 'overlapping input/output paths' in run(
        *command, '--output', nested_output, '--previous-source', old, success=False).stderr
    assert not nested_output.exists()
    assert sorted(p.name for p in old.iterdir()) == previous_entries
    assert old.stat().st_mtime_ns == previous_directory_mtime
    (old / 'include/v8config.h').write_text('tampered previous payload\n')
    rejected = work / 'rejected'
    run(*command, '--output', rejected, '--previous-source', old, success=False)
    assert not rejected.exists()
print('PASS: V8 previous source preserves unchanged patched header mtime, not changed GN mtime')
