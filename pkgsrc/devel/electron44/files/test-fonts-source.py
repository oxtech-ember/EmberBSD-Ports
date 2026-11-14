# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD contributors (AI-assisted).
"""Authenticated Chromium test-fonts input for the selected serial test."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

# Prepared-source identity only; this is not a runtime package.
PACKAGE = 'devel/electron-test-fonts'
IDENTITY = {'object':'9c07d19d9c5ee1ff94f717e6fb17e0c8c354e6f9',
            'sha256':'f0e9628f9e43e3f3476cde06a1849058de460e0e037b7449ce0d42b9a73c37d5',
            'size':33413117, 'generation':1775663926405386}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def verify_deps(workspace, git):
    src = Path(workspace) / 'src'
    run = lambda *args: subprocess.run([str(git), '-C', str(src), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')).stdout
    deps = run('show', 'HEAD:DEPS').decode('utf-8')
    return validate_deps(deps)

def validate_deps(deps):
    matches = re.findall(r"'src/third_party/test_fonts/test_fonts'\s*:\s*\{(.*?)\n  \},", deps, re.S)
    require(len(matches) == 1, 'Chromium test-fonts DEPS entry missing or ambiguous')
    block = matches[0]
    numeric = {}
    for field in ('size_bytes', 'generation'):
        values = re.findall(r"'" + field + r"'\s*:\s*([0-9]+)(?=\s*[,}\n])", block)
        require(len(values) == 1, 'Chromium test-fonts DEPS identity changed')
        numeric[field] = int(values[0])
    require("'dep_type': 'gcs'" in block and "'bucket': 'chromium-fonts'" in block and
            "'object_name': '" + IDENTITY['object'] + "'" in block and
            "'sha256sum': '" + IDENTITY['sha256'] + "'" in block and
            numeric['size_bytes'] == IDENTITY['size'] and
            numeric['generation'] == IDENTITY['generation'],
            'Chromium test-fonts DEPS identity changed')
    return IDENTITY

def prepare(sdk, workspace, git, archive, destination):
    identity = verify_deps(workspace, git)
    archive = Path(archive); destination = Path(destination)
    require(archive.is_absolute() and destination.is_absolute() and not os.path.lexists(destination), 'invalid test-fonts paths')
    f, before = sdk['paths'].open_regular(str(archive))
    with f:
        data = f.read(IDENTITY['size'] + 1)
    sdk['paths'].verify_stable(str(archive), before)
    require(len(data) == IDENTITY['size'] and hashlib.sha256(data).hexdigest() == IDENTITY['sha256'], 'test-fonts archive mismatch')
    # A fresh sibling stage is published atomically only after the SDK receipt.
    with tempfile.TemporaryDirectory(prefix='.electron-test-fonts-', dir=destination.parent) as tmp:
        stage = Path(tmp) / 'source'; stage.mkdir()
        # Extract from a private copy of the verified bytes.
        staged_archive = Path(tmp) / 'archive.tar.gz'
        staged_archive.write_bytes(data)
        sdk['sourceprep'].extract_archive(str(staged_archive), stage, 'test_fonts', 'Chromium test fonts', layout='flat')
        require((stage / 'test_fonts/Ahem.ttf').is_file(), 'Ahem.ttf missing')
        sdk['sourceprep'].write_prepared_tree_receipt(str(stage), package=PACKAGE, identity=identity)
        sdk['publication'].publish_directory_noreplace(str(stage), str(destination))

def validate(sdk, workspace, git, source):
    identity = verify_deps(workspace, git)
    source = Path(source)
    require(source.is_absolute() and source.is_dir() and not source.is_symlink(), 'invalid test-fonts source')
    sdk['sourceprep'].validate_prepared_tree(str(source), package=PACKAGE, identity=identity)
    target = source.resolve(strict=True) / 'test_fonts'
    require(target.is_dir() and not target.is_symlink(), 'invalid test-fonts tree')
    return target

def recover(work, workspace, target):
    marker = Path(work) / 'serial-test-fonts-link.json'
    link = Path(workspace) / 'src/third_party/test_fonts/test_fonts'
    require(link.parent.is_dir() and not link.parent.is_symlink(), 'invalid test-fonts link parent')
    if not os.path.lexists(marker):
        require(not os.path.lexists(link), 'foreign test-fonts link or directory')
        return
    require(marker.is_file() and not marker.is_symlink(), 'invalid test-fonts link marker')
    require(json.loads(marker.read_text()) == {'link':str(link), 'target':str(target)}, 'foreign test-fonts link marker')
    if os.path.lexists(link):
        require(link.is_symlink() and os.readlink(link) == str(target), 'foreign test-fonts link')
        link.unlink()
    marker.unlink()

@contextmanager
def linked(work, workspace, target):
    marker = Path(work) / 'serial-test-fonts-link.json'
    link = Path(workspace) / 'src/third_party/test_fonts/test_fonts'
    recover(work, workspace, target)
    # Publish complete marker before creating the link.
    with tempfile.NamedTemporaryFile(mode='w', dir=marker.parent, prefix='.test-fonts-link-', delete=False) as f:
        temporary = Path(f.name)
        json.dump({'link':str(link), 'target':str(target)}, f, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.link(temporary, marker)
    finally:
        temporary.unlink()
    try:
        link.symlink_to(target, target_is_directory=True)
        yield
    finally:
        recover(work, workspace, target)

if __name__ == '__main__':
    import argparse
    import importlib.util
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('workspace', 'ports-source', 'sdk-source', 'archive', 'destination', 'git', 'lock-root'):
        parser.add_argument('--' + option, type=Path, required=True)
    args = parser.parse_args()
    for value in vars(args).values():
        require(value.is_absolute(), 'all paths must be absolute')
    spec = importlib.util.spec_from_file_location('electron_owner', Path(__file__).with_name('build-electron.py'))
    owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner)
    sdk = owner.load_sdk(args.sdk_source)
    for path in (args.workspace, args.ports_source, args.sdk_source, args.archive, args.git, args.lock_root):
        sdk['paths'].reject_overlap(str(args.destination), str(path))
    exclusive = owner.context_keys(args.workspace, args.destination)
    shared = [x for x in owner.context_keys(args.ports_source, args.sdk_source, args.archive) if x not in exclusive]
    with sdk['process'].ContextLocks(exclusive, str(args.lock_root)):
        with sdk['process'].ContextLocks(shared, str(args.lock_root), shared=True):
            owner.verify_source(args.workspace, args.ports_source, args.git)
            prepare(sdk, args.workspace, args.git, args.archive, args.destination)
            owner.verify_source(args.workspace, args.ports_source, args.git)
    print('Prepared selected Chromium test fonts:', args.destination)
