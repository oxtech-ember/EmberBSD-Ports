#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the real inspector producer and exporter with a small Git fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for option in ('archive', 'sdk-source', 'git', 'patch', 'work-dir'):
    p.add_argument('--' + option, type=Path, required=True)
a = p.parse_args()
ports = Path(__file__).resolve().parents[3]

def run(args, *, success=True):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(f'{args!r}: {result.stderr}')
    return result

with tempfile.TemporaryDirectory(dir=a.work_dir) as temp:
    root = Path(temp) / 'ports'
    upstream = root / 'upstream/pkgsrc'
    (upstream / 'mk').mkdir(parents=True)
    (upstream / 'mk/bsd.pkg.mk').write_text('# fixture\n')
    run([a.git, '-C', upstream, 'init', '-q'])
    run([a.git, '-C', upstream, 'add', '-f', 'mk/bsd.pkg.mk'])
    run([a.git, '-C', upstream, '-c', 'user.name=Fixture', '-c',
         'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'])
    revision = run([a.git, '-C', upstream, 'rev-parse', 'HEAD']).stdout.strip()
    for relative in ('scripts/prepare-pkgsrc.py', 'scripts/pkgsrc-source-identity.py',
                     'scripts/source-inputs/inspector-protocol/source.py', 'pkgsrc/lang/llvm/files/sdk_source.py'):
        dest = root / relative; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ports / relative, dest)
    (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME= llvm-fixture\n')
    recipe = root / 'pkgsrc/devel/inspector-protocol'
    shutil.copytree(ports / 'pkgsrc/devel/inspector-protocol', recipe)
    patchdir = recipe / 'patches'; patchdir.mkdir()
    delta = b'--- /dev/null\n+++ fixture-patch-marker\n@@ -0,0 +1 @@\n+fixture\n'
    (patchdir / 'patch-fixture').write_bytes(delta)
    with (recipe / 'distinfo').open('ab') as info:
        info.write(b'SHA1 (patch-fixture) = ' + hashlib.sha1(delta).hexdigest().encode() + b'\n')
    (root / 'pkgsrc/export.conf').write_text(
        'file\tscripts/pkgsrc-source-identity.py\tEMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py\n')
    run([a.git, '-C', root, 'init', '-q'])
    run([a.git, '-C', root, 'add', 'pkgsrc/export.conf'])
    run([a.git, '-C', root, 'update-index', '--add', '--cacheinfo',
         f'160000,{revision},upstream/pkgsrc'])
    owner = root / 'scripts/source-inputs/inspector-protocol/source.py'
    base = [sys.executable, '-B', '-I', '-S', owner, '--sdk-source', a.sdk_source, '--git', a.git]
    output = Path(temp) / 'prepared'
    run([*base, 'prepare', '--archive', a.archive, '--patch', a.patch, '--output', output])
    assert (output / 'fixture-patch-marker').read_bytes() == b'fixture\n'
    exported = Path(temp) / 'exported'; exporter = root / 'scripts/prepare-pkgsrc.py'
    run([sys.executable, '-B', exporter, exported, '--git', a.git, '--patch', a.patch])
    current = [*base, 'verify-source', '--source', output, '--pkgsrc-root', exported]
    run(current)
    staged = Path(temp) / 'package-source'
    shutil.copytree(output, staged)
    (staged / 'emberbsd-prepared-source.json').unlink()
    stamp = recipe / 'files/stamp-source.py'
    run([sys.executable, '-B', '-I', '-S', stamp, '--sdk-source', a.sdk_source,
         '--source', staged, '--pkgsrc-root', exported])
    package_record = json.loads(run([*base, 'verify-source', '--source', staged,
                                     '--pkgsrc-root', exported]).stdout)
    producer_record = json.loads(run(current).stdout)
    assert package_record['tree_sha256'] == producer_record['tree_sha256']
    run([sys.executable, '-B', '-I', '-S', owner, '--sdk-source', a.sdk_source,
         'verify-payload', '--source', output])
    run([*base, 'prepare', '--archive', a.archive, '--patch', a.patch, '--output', output], success=False)
    target = output / 'code_generator.py'; before = target.read_bytes()
    target.write_bytes(before + b'\n# changed\n')
    assert 'payload changed' in run(current, success=False).stderr
    target.write_bytes(before); run(current)
    unrelated = root / 'pkgsrc/devel/unrelated'; unrelated.mkdir(parents=True)
    (unrelated / 'Makefile').write_text('DISTNAME= unrelated-1\n')
    export2 = Path(temp) / 'exported-unrelated'
    run([sys.executable, '-B', exporter, export2, '--git', a.git, '--patch', a.patch])
    current2 = [*base, 'verify-source', '--source', output, '--pkgsrc-root', export2]
    run(current2)
    patch = export2 / 'devel/inspector-protocol/patches/patch-fixture'; before = patch.read_bytes()
    patch.write_bytes(before + b'\n# changed\n')
    assert 'effective package changed' in run(current2, success=False).stderr
    patch.write_bytes(before); run(current2)
print('PASS: real exporter, selected patch, payload and scoped recipe checks')
