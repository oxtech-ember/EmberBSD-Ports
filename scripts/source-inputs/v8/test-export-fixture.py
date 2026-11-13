#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the real V8 producer/exporter against a small pkgsrc Git fixture."""
import argparse
import hashlib
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for arg in ('archive', 'sdk-source', 'git', 'patch', 'work-dir'):
    parser.add_argument('--' + arg, required=True, type=Path)
a = parser.parse_args()
ports = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(a.sdk_source / "src"))
from emberbsd_sdk.sourceprep import PREPARED_TREE_RECEIPT


def run(argv, success=True):
    result = subprocess.run([str(x) for x in argv], capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(f'{argv!r}: {result.stderr}')
    return result


with tempfile.TemporaryDirectory(prefix='v8-export-test-', dir=a.work_dir) as directory:
    work = Path(directory)
    root = work / 'ports'
    upstream = root / 'upstream/pkgsrc'
    upstream.mkdir(parents=True)
    (upstream / 'README').write_text('fixture upstream\n')
    run([a.git, '-C', upstream, 'init', '-q'])
    run([a.git, '-C', upstream, 'add', 'README'])
    run([a.git, '-C', upstream, '-c', 'user.name=Fixture', '-c',
         'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'])
    revision = run([a.git, '-C', upstream, 'rev-parse', 'HEAD']).stdout.strip()
    for name in ('scripts/prepare-pkgsrc.py', 'scripts/pkgsrc-source-identity.py', 'scripts/prepared_receipt.py',
                 'scripts/source-inputs/v8/source.py', 'pkgsrc/lang/llvm/files/sdk_source.py'):
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ports / name, dest)
    shutil.copytree(ports / 'pkgsrc/lang/v8', root / 'pkgsrc/lang/v8')
    (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME= llvm-fixture\n')
    (root / 'pkgsrc/export.conf').write_text(
        'file\tscripts/pkgsrc-source-identity.py\tEMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py\n'
        'file\tscripts/source-inputs/v8/source.py\tEMBERBSD-SOURCE-IDENTITY/v8-source.py\n')
    (root / 'pkgsrc/replaces').write_text('# fixture\n')
    run([a.git, '-C', root, 'init', '-q'])
    run([a.git, '-C', root, 'add', 'pkgsrc/export.conf'])
    run([a.git, '-C', root, 'update-index', '--add', '--cacheinfo',
         f'160000,{revision},upstream/pkgsrc'])
    archive = work / 'v8-15.6.75.57-5e51e9c6079c7fa65ca75e7919c81ea50734302e.tar.gz'
    shutil.copyfile(a.archive, archive)
    owner = root / 'scripts/source-inputs/v8/source.py'
    command = [sys.executable, '-B', '-I', '-S', owner, '--sdk-source', a.sdk_source,
               '--git', a.git]
    output = work / 'prepared'
    run([*command, 'prepare', '--archive', archive, '--patch', a.patch, '--output', output])
    def export(name):
        result = work / name
        run([sys.executable, '-B', root / 'scripts/prepare-pkgsrc.py', result,
             '--git', a.git, '--patch', a.patch])
        return result
    baseline = export('export-baseline')
    # The actual selected V8 generator binds code-cache salt to its prepared
    # tree receipt; a different valid tree changes it and malformed input fails.
    import json
    selected_receipt = output / PREPARED_TREE_RECEIPT
    record = json.loads(selected_receipt.read_text())
    alternate = work / 'alternate-receipt.json'
    changed = dict(record, tree_sha256=('0' if record['tree_sha256'][0] != '0' else '1') + record['tree_sha256'][1:])
    alternate.write_text(json.dumps(changed))
    generator = output / 'tools/gen-version-hash-salt.py'
    salt_a = run([sys.executable, '-B', generator, '--receipt', selected_receipt]).stdout.strip()
    salt_b = run([sys.executable, '-B', generator, '--receipt', alternate]).stdout.strip()
    assert salt_a == record['tree_sha256'][:16] and salt_b == changed['tree_sha256'][:16] and salt_a != salt_b
    header = work / 'cache-salt.h'
    run([sys.executable, '-B', generator, '--header', header, '--build-root', work, '--receipt', selected_receipt])
    assert header.read_text() == '#define V8_VERSION_HASH_SALT "' + salt_a + '"\n'
    alternate.write_text('{}')
    assert 'invalid V8 prepared source receipt' in run([sys.executable, '-B', generator, '--receipt', alternate], False).stderr
    gn = (output / 'gni/version_hash_salt.gni').read_text()
    assert 'v8_prepared_source_receipt' in gn and '--receipt' in gn
    run([sys.executable, '-B', '-I', '-S', owner, '--sdk-source', a.sdk_source,
         'verify-payload', '--source', output])
    run([*command, 'verify-source', '--source', output, '--pkgsrc-root', baseline])
    package_tree = work / 'package-tree'
    package_tree.mkdir()
    (package_tree / 'sample').write_text('same SDK content identity')
    run([sys.executable, '-B', baseline / 'lang/v8/files/stamp-source.py',
         '--sdk-source', a.sdk_source, '--source', package_tree, '--pkgsrc-root', baseline])
    run([*command, 'verify-payload', '--source', package_tree])
    run([*command, 'verify-source', '--source', package_tree, '--pkgsrc-root', baseline])
    # A stamped package must bind the same producer as the source CLI.
    import json
    receipt = package_tree / PREPARED_TREE_RECEIPT
    saved = receipt.read_bytes()
    forged = json.loads(saved)
    forged['identity']['owner_sha256'] = '0' * 64
    receipt.write_text(json.dumps(forged))
    assert 'V8 source producer changed' in run(
        [*command, 'verify-source', '--source', package_tree, '--pkgsrc-root', baseline], False).stderr
    receipt.write_bytes(saved)
    run([*command, 'prepare', '--archive', archive, '--patch', a.patch, '--output', output], False)
    unrelated = root / 'pkgsrc/devel/unrelated/Makefile'
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text('DISTNAME= unrelated-1\n')
    run([*command, 'verify-source', '--source', output, '--pkgsrc-root', export('export-unrelated')])
    package = root / 'pkgsrc/lang/v8'
    patchfile = next((package / 'patches').glob('patch-*'))
    original_patch = patchfile.read_bytes()
    distinfo = package / 'distinfo'
    original_info = distinfo.read_text()
    patchfile.write_bytes(original_patch + b'\n# changed\n')
    filtered = b''.join(line for line in patchfile.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)
    changed_info = re.sub(r'(?m)^SHA1 \(' + re.escape(patchfile.name) + r'\) = [0-9a-f]{40}$',
                          'SHA1 (' + patchfile.name + ') = ' + hashlib.sha1(filtered).hexdigest(), original_info)
    assert changed_info != original_info
    distinfo.write_text(changed_info)
    assert 'V8 effective recipe changed' in run(
        [*command, 'verify-source', '--source', output, '--pkgsrc-root', export('export-changed-patch')], False).stderr
    patchfile.write_bytes(original_patch)
    distinfo.write_text(original_info.replace('BLAKE2s (', 'BLAKE2s (', 1).replace(' = ', ' = 0', 1))
    assert 'V8 effective recipe changed' in run(
        [*command, 'verify-source', '--source', output, '--pkgsrc-root', export('export-changed-archive')], False).stderr
    distinfo.write_text(original_info)
    target = output / 'include/v8-version.h'
    before = target.read_bytes()
    target.write_bytes(before + b'\n/* changed */\n')
    assert 'payload changed' in run([*command, 'verify-payload', '--source', output], False).stderr
    target.write_bytes(before)
    run([*command, 'verify-source', '--source', output, '--pkgsrc-root', baseline])
print('PASS: real exporter, V8 source preparation and change refusal')
