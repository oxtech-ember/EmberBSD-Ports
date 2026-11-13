#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Node producer reuse through the real SDK with a tiny source fixture."""
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


with tempfile.TemporaryDirectory(prefix='node-reuse-fixture-', dir=args.work_dir) as directory:
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
                 'scripts/prepared_receipt.py', 'scripts/source-inputs/node/source.py',
                 'profiles/common-build-tools/node-prune-npm-gyp.py',
                 'pkgsrc/lang/llvm/files/sdk_source.py'):
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ports / name, destination)
    package = root / 'pkgsrc/lang/nodejs'
    (package / 'patches').mkdir(parents=True)
    (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME= llvm-fixture\n')
    (root / 'pkgsrc/export.conf').write_text('file\tscripts/pkgsrc-source-identity.py\tEMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py\n'
        'file\tprofiles/common-build-tools/node-prune-npm-gyp.py\tlang/nodejs/files/node-prune-npm-gyp.py\n')
    (root / 'pkgsrc/replaces').write_text('# fixture\n')
    run(args.git, '-C', root, 'init', '-q')
    run(args.git, '-C', root, 'add', 'pkgsrc/export.conf')
    run(args.git, '-C', root, 'update-index', '--add', '--cacheinfo',
        f'160000,{pin},upstream/pkgsrc')
    archive = work / 'node-v1.2.3.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for directory in ('deps/npm/node_modules/node-gyp/gyp',
                          'deps/npm/node_modules/node-gyp/gyp/pylib',
                          'deps/npm/node_modules/node-gyp/gyp/pylib/gyp'):
            entry = tarfile.TarInfo('node-v1.2.3/' + directory)
            entry.type, entry.mode, entry.mtime = tarfile.DIRTYPE, 0o755, 1000000000
            tar.addfile(entry)
        for name, data in [('include/node.h', 'original header\n'),
                           ('node.gyp', 'original gyp\n'),
                           ('deps/npm/node_modules/node-gyp/package.json', '{"name":"node-gyp"}'),
                           ('deps/npm/node_modules/node-gyp/lib/configure.js', "process.env.NODE_GYP_SOURCE; 'share/gyp';"),
                           ('deps/npm/node_modules/node-gyp/gyp/gyp_main.py', 'original backend\n'),
                           ('deps/npm/node_modules/node-gyp/gyp/pylib/gyp/__init__.py', 'original backend\n')]:
            payload = data.encode()
            info = tarfile.TarInfo('node-v1.2.3/' + name)
            info.size, info.mode, info.mtime = len(payload), 0o644, 1000000000
            tar.addfile(info, io.BytesIO(payload))
    archive_data = archive.read_bytes()
    header_patch = '--- include/node.h\n+++ include/node.h\n@@ -1 +1 @@\n-original header\n+patched header\n'
    def recipe(gyp_value, revision_number):
        (package / 'Makefile').write_text(f'DISTNAME= node-v1.2.3\nEXTRACT_SUFX= .tar.gz\nPKGREVISION= {revision_number}\n')
        patches = {'patch-header': header_patch, 'patch-gyp': '--- node.gyp\n+++ node.gyp\n@@ -1 +1 @@\n-original gyp\n+' + gyp_value + '\n'}
        if revision_number == 2:
            patches['patch-new'] = '--- /dev/null\n+++ new-file\n@@ -0,0 +1 @@\n+new input\n'
        for name, contents in patches.items():
            (package / 'patches' / name).write_text(contents)
        lines = [f'BLAKE2s ({archive.name}) = {hashlib.blake2s(archive_data).hexdigest()}',
                 f'SHA512 ({archive.name}) = {hashlib.sha512(archive_data).hexdigest()}',
                 f'Size ({archive.name}) = {len(archive_data)} bytes']
        lines.extend(f'SHA1 ({name}) = {hashlib.sha1(text.encode()).hexdigest()}'
                     for name, text in sorted(patches.items()))
        (package / 'distinfo').write_text('\n'.join(lines) + '\n')

    owner = root / 'scripts/source-inputs/node/source.py'
    command = [sys.executable, '-B', '-I', '-S', owner, '--sdk-source', args.sdk_source,
               '--git', args.git, 'prepare', '--archive', archive, '--patch', args.patch]
    old, new = work / 'old', work / 'new'
    recipe('gn one', 1)
    run(*command, '--output', old)
    fixed_ns = 1100000000000000000
    for name in ('include/node.h', 'node.gyp'):
        os.utime(old / name, ns=(fixed_ns, fixed_ns))
    recipe('gn two', 2)
    run(*command, '--output', new, '--previous-source', old)
    assert (old / 'include/node.h').read_bytes() == (new / 'include/node.h').read_bytes()
    assert (new / 'include/node.h').stat().st_mtime_ns == fixed_ns
    assert (old / 'node.gyp').read_bytes() != (new / 'node.gyp').read_bytes()
    assert (new / 'node.gyp').stat().st_mtime_ns != fixed_ns
    assert not (old / 'new-file').exists()
    assert (new / 'new-file').read_text() == 'new input\n'
    assert not (new / 'deps/npm/node_modules/node-gyp/gyp').exists()
    assert (new / 'new-file').stat().st_mtime_ns != fixed_ns
    assert (old / 'include/node.h').stat().st_mtime_ns == fixed_ns
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
    (old / 'include/node.h').write_text('tampered previous payload\n')
    rejected = work / 'rejected'
    run(*command, '--output', rejected, '--previous-source', old, success=False)
    assert not rejected.exists()
print('PASS: Node previous source preserves unchanged patched header mtime, not changed gyp mtime')
