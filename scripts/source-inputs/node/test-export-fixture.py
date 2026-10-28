#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the real Node producer and pkgsrc exporter with a small Git fixture."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for option in ('upstream-pkgsrc', 'node-overlay', 'gc-patch', 'extra-patch',
               'archive', 'sdk-source', 'git', 'patch', 'work-dir'):
    parser.add_argument('--' + option, type=Path, required=True)
a = parser.parse_args()
ports = Path(__file__).resolve().parents[3]

def run(args, *, success=True):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(f'{args!r}: {result.stderr}')
    return result

with tempfile.TemporaryDirectory(dir=a.work_dir) as temp:
    root = Path(temp) / 'ports'
    upstream = root / 'upstream/pkgsrc'
    (upstream / 'lang').mkdir(parents=True)
    shutil.copytree(a.upstream_pkgsrc / 'lang/nodejs', upstream / 'lang/nodejs')
    run([a.git, '-C', upstream, 'init', '-q'])
    run([a.git, '-C', upstream, 'add', '-f', 'lang/nodejs'])
    run([a.git, '-C', upstream, '-c', 'user.name=Fixture', '-c',
         'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'])
    revision = run([a.git, '-C', upstream, 'rev-parse', 'HEAD']).stdout.strip()
    for relative in ('scripts/prepare-pkgsrc.py', 'scripts/pkgsrc-source-identity.py',
                     'scripts/source-inputs/node/source.py', 'pkgsrc/lang/llvm/files/sdk_source.py'):
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ports / relative, dest)
    (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME= llvm-fixture\n')
    patch_dir = root / 'profiles/common-build-tools/patches'
    patch_dir.mkdir(parents=True)
    for path, name in ((a.node_overlay, 'node-overlay.patch'), (a.gc_patch, 'node-gc.patch'),
                       (a.extra_patch, 'node-extra.patch')):
        shutil.copy2(path, patch_dir / name)
    (root / 'pkgsrc/export.conf').write_text(
        'patch\tprofiles/common-build-tools/patches/node-overlay.patch\n'
        'recipe-patch\tprofiles/common-build-tools/patches/node-gc.patch\tlang/nodejs\t'
        'patch-test_parallel_test-gc-net-timeout.js\n'
        'recipe-patch\tprofiles/common-build-tools/patches/node-extra.patch\tlang/nodejs\t'
        'patch-node-extra\n')
    run([a.git, '-C', root, 'init', '-q'])
    run([a.git, '-C', root, 'add', 'pkgsrc/export.conf'])
    run([a.git, '-C', root, 'update-index', '--add', '--cacheinfo',
         f'160000,{revision},upstream/pkgsrc'])
    owner = root / 'scripts/source-inputs/node/source.py'
    base = [sys.executable, '-B', '-I', '-S', owner, '--sdk-source', a.sdk_source,
            '--git', a.git]
    output = Path(temp) / 'prepared'
    run([*base, 'prepare', '--archive', a.archive, '--patch', a.patch, '--output', output])
    exported = Path(temp) / 'exported'
    exporter = root / 'scripts/prepare-pkgsrc.py'
    run([sys.executable, '-B', exporter, exported, '--git', a.git, '--patch', a.patch])
    exported_output = Path(temp) / 'prepared-export'
    direct_base = [sys.executable, '-B', '-I', '-S', owner, '--sdk-source', a.sdk_source]
    run([*direct_base, 'prepare', '--pkgsrc-root', exported, '--archive', a.archive,
         '--patch', a.patch, '--output', exported_output])
    first = json.loads((output / 'emberbsd-prepared-source.json').read_text())
    second = json.loads((exported_output / 'emberbsd-prepared-source.json').read_text())
    assert first['tree_sha256'] == second['tree_sha256']
    run([*direct_base, 'verify-source', '--source', exported_output, '--pkgsrc-root', exported])
    run([*direct_base, 'prepare', '--pkgsrc-root', 'relative', '--archive', a.archive,
         '--patch', a.patch, '--output', Path(temp) / 'invalid'], success=False)
    current = ['verify-source', '--source', output, '--pkgsrc-root', exported]
    run([*base, *current])
    run([sys.executable, '-B', '-I', '-S', owner, '--sdk-source', a.sdk_source,
         'verify-payload', '--source', output])
    run([*base, 'prepare', '--archive', a.archive, '--patch', a.patch, '--output', output],
        success=False)
    target = output / 'src/node_version.h'
    before = target.read_bytes()
    target.write_bytes(before + b'\n/* changed */\n')
    assert 'payload changed' in run([*base, *current], success=False).stderr
    target.write_bytes(before)
    run([*base, *current])
    unrelated = root / 'pkgsrc/devel/unrelated'
    unrelated.mkdir(parents=True)
    (unrelated / 'Makefile').write_text('DISTNAME= unrelated-1\n')
    export2 = Path(temp) / 'exported-unrelated'
    run([sys.executable, '-B', exporter, export2, '--git', a.git, '--patch', a.patch])
    run([*base, 'verify-source', '--source', output, '--pkgsrc-root', export2])
    distinfo = export2 / 'lang/nodejs/distinfo'
    original = distinfo.read_bytes()
    distinfo.write_bytes(original + b'\n# changed recipe\n')
    assert 'effective package changed' in run([*base, 'verify-source', '--source', output,
        '--pkgsrc-root', export2], success=False).stderr
    distinfo.write_bytes(original)
    node_patch = export2 / 'lang/nodejs/patches/patch-node-extra'
    original_patch = node_patch.read_bytes()
    node_patch.write_bytes(original_patch + b'\n# changed patch\n')
    assert 'effective package changed' in run([*base, 'verify-source', '--source', output,
        '--pkgsrc-root', export2], success=False).stderr
    node_patch.write_bytes(original_patch)
    run([*base, 'verify-source', '--source', output, '--pkgsrc-root', export2])
print('PASS: real pkgsrc export, common Node source, patch inventory and change refusal')
