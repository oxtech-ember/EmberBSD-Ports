# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; failed external-support checkpoint policy.
from pathlib import Path
import re
import shutil
from emberbsd_sdk import inventory, paths
from host import require, sha, digest_rows, assert_recoverable
from runtime import field
from resume_state import verify_hash_rows


def tree_manifests(tree):
    records = inventory.snapshot_tree(tree)
    return {'inventory': '\n'.join(sorted(['.'] + ['./' + name for name in records])) + '\n', 'sha256': ''.join(sorted(record['sha256'] + '  ./' + name + '\n' for name, record in records.items() if record['kind'] == 'file')), 'symlinks': ''.join('./' + name + '\t' + record['target'] + '\n' for name, record in records.items() if record['kind'] == 'link')}


def phase_guard(work):
    for name in ('src', 'build', 'build/gcc', 'stage'):
        paths.real_directory(work / name)
    for name in ('build-success', 'external-runtime-plan.txt', 'build/gcc/cc1', 'build/gcc/cc1plus'):
        require(paths.entry(work / name) is None, 'Target runtime/frontend phase already started')
    require(not any(record['kind'] in ('file', 'link') for record in inventory.snapshot_tree(work / 'stage').values()), 'Target stage is not empty')
    inputs = (work / 'inputs.txt').read_text()
    target = work / 'build' / field(inputs, 'triplet')
    require(not target.exists() or not any(record['kind'] in ('file', 'link') for record in inventory.snapshot_tree(target).values()), 'Target library objects already exist')
    require(field(inputs, 'scope') == 'runtime-only-external-compiler', 'External support scope required')
    return inputs


def support(action, work, failure=None):
    work = Path(work).resolve(strict=True)
    assert_recoverable(work)
    parent = work / 'support-parent'
    inputs = phase_guard(work)
    if action == 'checkpoint':
        require(failure and re.fullmatch(r'[1-9][0-9]*\n?', Path(failure).read_text()), 'Nonzero parent failure exit required')
        require(paths.entry(parent) is None, 'Support checkpoint already exists')
        paths.regular_file(work / 'support-build.log')
        verify_hash_rows(inputs)
        parent.mkdir(); (parent / 'helpers').mkdir()
        for name in ('inputs.txt', 'external-compiler.txt', 'support-build.log', 'support-host.log', 'configure.log', 'patch.log'):
            shutil.copy2(work / name, parent / name)
        shutil.copy2(failure, parent / 'failure-exit.txt')
        helper_root = Path(__file__).resolve().parent
        helpers = []
        for line in inputs.splitlines():
            match = re.fullmatch(r'[0-9a-f]{64}  (.+)', line)
            if match and Path(match[1]).parent == helper_root and Path(match[1]).suffix == '.py':
                shutil.copy2(match[1], parent / 'helpers' / Path(match[1]).name)
                helpers.append(parent / 'helpers' / Path(match[1]).name)
        require(helpers, 'Missing Python controller source identity')
        (parent / 'helper-prefix.txt').write_text(str(helper_root) + '\n')
        (parent / 'phase').write_text('failed-external-support\n')
        shutil.copy2(__file__, parent / 'checkpoint-producer.py')
        (parent / 'checkpoint-producer.sha256').write_text(digest_rows([parent / 'checkpoint-producer.py']))
        (parent / 'helpers.sha256').write_text(digest_rows(sorted(helpers)))
        for tag, tree in [('source', work / 'src'), ('build', work / 'build'), ('seed', Path(field(inputs, 'sysroot')))]:
            for kind, value in tree_manifests(tree).items():
                (parent / (tag + '.' + kind)).write_text(value)
        (work / 'support-parent.sha256').write_text(digest_rows(sorted(path for path in parent.iterdir() if path.is_file())))
        return
    require(action in ('check', 'resume') and failure is None, 'Unknown support action or extra arguments')
    paths.real_directory(parent)
    verify_hash_rows((work / 'support-parent.sha256').read_text())
    verify_hash_rows((parent / 'helpers.sha256').read_text())
    require(inputs == (parent / 'inputs.txt').read_text(), 'Original receipt changed')
    require((work / 'external-compiler.txt').read_bytes() == (parent / 'external-compiler.txt').read_bytes(), 'Original compiler identity changed')
    require((parent / 'phase').read_text() == 'failed-external-support\n', 'Wrong parent failure phase')
    prefix = (parent / 'helper-prefix.txt').read_text().rstrip('\n')
    mapping = {}
    for line in inputs.splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if match and Path(match[2]).parent == Path(prefix) and Path(match[2]).suffix in ('.sh', '.py'):
            frozen = parent / 'helpers' / Path(match[2]).name
            require(sha(frozen) == match[1], 'Frozen helper source differs from original receipt')
            mapping[match[2]] = str(frozen)
    verify_hash_rows(inputs, mapping)
    for tag, tree in [('source', work / 'src'), ('build', work / 'build'), ('seed', Path(field(inputs, 'sysroot')))]:
        for kind, value in tree_manifests(tree).items():
            require(value == (parent / (tag + '.' + kind)).read_text(), 'Support checkpoint tree changed: ' + tag + '/' + kind)
    if action == 'resume':
        rewritten = inputs
        for original, frozen in mapping.items():
            rewritten = rewritten.replace('  ' + original + '\n', '  ' + frozen + '\n')
        rewritten = rewritten.replace('scope=runtime-only-external-compiler\n', 'scope=runtime-only-external-support-resume\n', 1)
        rewritten += 'resume_support_prior_inputs_sha256=' + sha(parent / 'inputs.txt') + '\n'
        rewritten += (work / 'support-parent.sha256').read_text() + digest_rows([work / 'support-parent.sha256'])
        rewritten += ''.join('historical_helper_map=' + original + '\t' + frozen + '\t' + sha(frozen) + '\n' for original, frozen in sorted(mapping.items()))
        (work / 'inputs.txt').write_text(rewritten)
