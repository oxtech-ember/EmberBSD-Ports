# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; preserve and authenticate incomplete runtime state.
from pathlib import Path
import re
import shutil
import tempfile
from emberbsd_sdk import inventory, paths
from host import require, sha, capture, digest_rows, assert_recoverable
from runtime import field
from runtime_libraries import check_prior, verify_completed_stage

FRONTEND_FILES = 'Makefile config.cache config.status config.log auto-host.h configargs.h xgcc cc1 cc1plus'.split()


def verify_hash_rows(value, mapping=None):
    found = False
    for line in value.splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if match:
            found = True
            file = mapping.get(match[2], match[2]) if mapping else match[2]
            require(sha(Path(file).resolve(strict=True)) == match[1], 'Original runtime input changed: ' + str(file))
    require(found, 'Missing original input hashes')


def check_resume(state):
    work = state.work
    assert_recoverable(work)
    for directory in ('src', 'build/gcc', 'stage'):
        paths.real_directory(work / directory)
    inputs = (work / 'inputs.txt').read_text()
    extension = check_prior(work, state.selection, state.resume)
    require(not (work / 'build-success').is_symlink(), 'Runtime success marker must not be symlink')
    if (work / 'build-success').exists():
        require(state.resume == 'runtime' and extension, 'Refusing completed stage without additional libraries')
        verify_completed_stage(work)
    if state.resume != 'runtime':
        require(not any(item['kind'] in ('file', 'link') for item in inventory.snapshot_tree(work / 'stage').values()), 'Resume requires uninstalled runtime stage')
    expected = {'scope': 'runtime-only-bootstrap', 'target': state.target, 'triplet': state.triplet, 'seed_source': state.origin, 'kernel': str(state.kernel), 'sysroot': str(state.sysroot), 'math': str(state.math), **state.host_fields()}
    for key, value in expected.items():
        if key not in ('host_ar', 'host_nm', 'host_ranlib'):
            require(field(inputs, key) == value, 'Resume input changed: ' + key)
    verify_hash_rows(inputs)
    xgcc = work / 'build/gcc/xgcc'
    require(capture([xgcc, '-dumpmachine']).strip() == state.triplet and capture([xgcc, '-dumpfullversion']).strip() == '16.2.0', 'Runtime frontend target/version changed')
    result = state.compiler_version(xgcc)
    require('Thread model: posix' in result.splitlines(), 'Resume requires POSIX-thread frontend')
    if state.resume == 'runtime':
        require('target_binutils=audited-kernel-prefix\n' in inputs, 'Runtime resume requires explicit target-binutils receipt')
        for name in FRONTEND_FILES:
            require((work / 'build/gcc' / name).is_file() and (work / 'build/gcc' / name).stat().st_size, 'Missing frontend state: ' + name)


def backup_generated(work, backup, name):
    source = work / 'build' / name
    if source.is_file() or source.is_symlink():
        target = backup / 'build' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)


def backup_resume(state):
    work = state.work
    assert_recoverable(work)
    runtime_only = state.resume == 'runtime'
    backup = Path(tempfile.mkdtemp(prefix='resume-runtime.' if runtime_only else 'resume.', dir=work))
    shutil.copy2(work / 'inputs.txt', backup / 'inputs.txt')
    for name in ('configure.log', 'frontends.log', 'frontend-version.txt', 'runtime-build.log', 'runtime-install.log'):
        if (work / name).is_file():
            shutil.copy2(work / name, backup / name)
    if runtime_only:
        for name in ('build-success', 'stage.sha256', 'stage.symlinks'):
            if (work / name).is_file():
                shutil.copy2(work / name, backup / ('original-' + name))
        for name in ('Makefile', 'config.status', 'config.log', 'config.cache'):
            if (work / 'build' / name).is_file():
                shutil.copy2(work / 'build' / name, backup / ('top-' + name))
        (backup / 'frontend.sha256').write_text(digest_rows([work / 'build/gcc' / name for name in FRONTEND_FILES]))
        tree = inventory.snapshot_tree(work / 'stage')
        from host import manifests
        manifests(work / 'stage', backup)
        (backup / 'stage.inventory').write_text('\n'.join(sorted(['.'] + ['./' + name for name in tree])) + '\n')
        (work / 'stage').rename(backup / 'stage')
        require(inventory.snapshot_tree(backup / 'stage') == tree, 'Partial-stage preservation failed')
        if (work / 'build-success').is_file():
            require((backup / 'stage.sha256').read_bytes() == (backup / 'original-stage.sha256').read_bytes() and (backup / 'stage.symlinks').read_bytes() == (backup / 'original-stage.symlinks').read_bytes(), 'Completed manifest changed during stage preservation')
            (work / 'build-success').rename(backup / 'build-success')
        (work / 'stage').mkdir()
        metadata = []
        root = work / 'build' / state.triplet
        for file in root.rglob('*'):
            if (file.is_file() or file.is_symlink()) and (file.name in ('Makefile', 'config.cache', 'config.status', 'config.log', 'libtool') or file.suffix in ('.la', '.lai')):
                metadata.append(str(file))
        (backup / 'target-metadata.paths').write_text(''.join(name + '\n' for name in sorted(metadata)))
        for name in metadata:
            backup_generated(work, backup, str(Path(name).relative_to(work / 'build')))
        additions = 'resume_runtime_prior_inputs_sha256=' + sha(backup / 'inputs.txt') + '\nresume_runtime_backup=' + str(backup) + '\nruntime_toolexeclibdir=/usr/pkg/gcc16/lib\n' + digest_rows([backup / name for name in ('frontend.sha256', 'stage.sha256', 'stage.symlinks', 'stage.inventory', 'target-metadata.paths')])
    else:
        names = ['gcc/Makefile', 'gcc/config.cache', 'gcc/nm'] + [state.triplet + '/' + name for name in ('libgcc/Makefile', 'libgcc/config.cache', 'libstdc++-v3/Makefile', 'libstdc++-v3/config.cache', 'libgcc/libgcc.map', 'libgcc/tmp-libgcc.map', 'libgcc/libgcc.a', 'libgcc/libgcc_eh.a', 'libgcc/libgcov.a')]
        names += [str(file.relative_to(work / 'build')) for file in (work / 'build' / state.triplet / 'libgcc').glob('libgcc_s.so*')]
        for name in names:
            backup_generated(work, backup, name)
        additions = 'resume_prior_inputs_sha256=' + sha(backup / 'inputs.txt') + '\nresume_backup=' + str(backup) + '\n'
    current = (work / 'inputs.txt').read_text()
    current = ''.join(line for line in current.splitlines(keepends=True) if not line.startswith('runtime_libraries='))
    (work / 'inputs.txt').write_text(current + 'runtime_libraries=' + state.selection + '\n' + additions)
    return backup


def verify_frontend(backup):
    verify_hash_rows((Path(backup) / 'frontend.sha256').read_text())
