#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Changed source rebuilds while equal source keeps the old effective mtime."""
import importlib.util
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch
import tempfile

sys.path.insert(0, str(Path(sys.argv[1]) / 'src'))
from emberbsd_sdk import inventory, sourceprep
from emberbsd_sdk.errors import SDKError
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ml', owner / '../../pkgsrc/devel/electron44/files/ml-source-projection.py')
ml = importlib.util.module_from_spec(spec); spec.loader.exec_module(ml)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary).resolve(); old = root/'old'; common=root/'common'; dest=root/'projected'; old.mkdir(); common.mkdir()
    for name, content in (('same.c','equal'),('changed.c','old')): (old/name).write_text(content)
    for name, content in (('same.c','equal'),('changed.c','new'),('added.c','added')): (common/name).write_text(content)
    past = time.time() - 10
    for path in old.iterdir():
        os.utime(path, (past, past))
    ninja = sys.argv[2]
    graph = root/'build.ninja'
    graph.write_text('rule copy\n  command = cp $in $out\nbuild same.o: copy view/same.c\nbuild changed.o: copy view/changed.c\nbuild unrelated.o: copy unrelated.c\n')
    (root/'unrelated.c').write_text('unrelated')
    (root/'view').symlink_to(old, target_is_directory=True)
    subprocess.run([ninja, '-f', str(graph)], cwd=root, check=True, capture_output=True)
    same_obj = ((root/'same.o').stat().st_ino, (root/'same.o').stat().st_mtime_ns)
    other_obj = ((root/'unrelated.o').stat().st_ino, (root/'unrelated.o').stat().st_mtime_ns)
    (old/'mode.c').write_text('same mode content')
    (common/'mode.c').write_text('same mode content')
    os.chmod(old/'mode.c', 0o644)
    os.chmod(common/'mode.c', 0o755)
    os.utime(old/'mode.c', (past, past))
    before=(old/'same.c').stat().st_mtime_ns
    (common/'internal').symlink_to('same.c')
    result=ml.prepare_projection(inventory,old,common,dest)
    assert (result/'internal').is_symlink() and (result/'internal').read_text() == 'equal'
    assert (result/'same.c').stat().st_mtime_ns == before
    assert (result/'changed.c').read_text() == 'new' and (result/'added.c').read_text() == 'added'
    assert (result/'mode.c').stat().st_mode & 0o777 == 0o755
    assert (result/'mode.c').stat().st_mtime_ns != (old/'mode.c').stat().st_mtime_ns
    assert (result/'changed.c').stat().st_mtime_ns != (old/'changed.c').stat().st_mtime_ns
    (root/'view').unlink()
    (root/'view').symlink_to(dest, target_is_directory=True)
    run = subprocess.run([ninja, '-f', str(graph)], cwd=root, check=True, capture_output=True, text=True)
    assert 'changed.o' in run.stdout and 'same.o' not in run.stdout and 'unrelated.o' not in run.stdout, run.stdout
    assert (root/'changed.o').read_text() == 'new'
    assert ((root/'same.o').stat().st_ino, (root/'same.o').stat().st_mtime_ns) == same_obj
    assert ((root/'unrelated.o').stat().st_ino, (root/'unrelated.o').stat().st_mtime_ns) == other_obj
    run = subprocess.run([ninja, '-f', str(graph)], cwd=root, check=True, capture_output=True, text=True)
    assert 'no work to do' in run.stdout, run.stdout
    class ChangedInventory:
        open_regular = staticmethod(inventory.open_regular)
        stable_identity = staticmethod(inventory.stable_identity)
        verify_stable = staticmethod(inventory.verify_stable)
        @staticmethod
        def snapshot_tree(path, **kwargs):
            result = inventory.snapshot_tree(path, **kwargs)
            if Path(path) == common:
                (common/'changed.c').write_text('changed after inventory')
            return result
    try:
        ml.prepare_projection(ChangedInventory, old, common, root/'raced')
    except ValueError:
        assert not (root/'raced').exists()
    else:
        raise AssertionError('changed source accepted after inventory')
    (root/'alias').symlink_to(common, target_is_directory=True)
    try:
        ml.prepare_projection(inventory, old, common, root/'alias/overlap')
    except ValueError:
        pass
    else:
        raise AssertionError('overlapping symlink parent accepted')
    cache = root/'cache'; cache.mkdir(mode=0o700)
    os.environ['EMBER_PREPARED_SOURCE_CACHE'] = str(cache)
    cached = root/'cached'
    identity = {'tree': 'selected-common-tree', 'subtree': 'src'}
    ml.prepare_projection(inventory, old, common, cached, sourceprep=sourceprep,
                          package='electron-view/fixture', identity=identity)
    time.sleep(1.05)  # SDK cache rejects metadata younger than its safety window.
    ml.validate_projection(sourceprep, cached, package='electron-view/fixture', identity=identity)
    cached_time = (cached/'same.c').stat().st_mtime_ns
    with patch.object(inventory, 'sha256_file', side_effect=AssertionError('unchanged payload rehashed')):
        ml.validate_projection(sourceprep, cached, package='electron-view/fixture', identity=identity)
    assert (cached/'same.c').stat().st_mtime_ns == cached_time
    header = root/'selected.h'; header.write_text('same header')
    old_headers = root/'old-headers'; old_headers.mkdir(); (old_headers/'selected.h').write_text('same header')
    os.utime(old_headers/'selected.h', (past, past))
    record = {'selected.h': {'path':str(header), 'md5':hashlib.md5(header.read_bytes()).hexdigest(),
                             'stable':list(inventory.stable_identity(header.stat()))}}
    projected_headers = ml.prepare_selected_projection(inventory, old_headers, record, root/'headers',
        sourceprep=sourceprep, package='electron-view/headers', identity={'package':'fixture'})
    assert (projected_headers/'selected.h').stat().st_mtime_ns == (old_headers/'selected.h').stat().st_mtime_ns
    wrong = {'selected.h': {**record['selected.h'], 'md5':'0'*32}}
    try:
        ml.prepare_selected_projection(inventory, old_headers, wrong, root/'wrong-md5',
            sourceprep=sourceprep, package='electron-view/headers', identity={'package':'fixture'})
    except ValueError:
        assert not (root/'wrong-md5').exists()
    else:
        raise AssertionError('wrong package checksum accepted')
    info = header.stat(); header.write_text('bad payload'); os.utime(header, ns=(info.st_atime_ns, info.st_mtime_ns))
    try:
        ml.prepare_selected_projection(inventory, old_headers, record, root/'bad-headers',
            sourceprep=sourceprep, package='electron-view/headers', identity={'package':'fixture'})
    except ValueError:
        assert not (root/'bad-headers').exists()
    else:
        raise AssertionError('modified installed header accepted')
    alias_old = root/'alias-old'; alias_old.mkdir()
    (alias_old/'same.c').write_text('different old alias')
    os.utime(alias_old/'same.c', (past, past))
    alias_dest = root/'alias-projection'
    ml.prepare_projection(inventory, old, common, alias_dest, old_aliases=[('.', alias_old)])
    assert (alias_dest/'same.c').stat().st_mtime_ns > (old/'same.c').stat().st_mtime_ns
    # Two prior consumers shared one resulting file after migration.
    (root/'first').symlink_to(old, target_is_directory=True)
    (root/'second').symlink_to(alias_old, target_is_directory=True)
    alias_graph = root/'alias.ninja'
    alias_graph.write_text('rule copy\n  command = cp $in $out\nbuild first.o: copy first/same.c\nbuild second.o: copy second/same.c\n')
    subprocess.run([ninja, '-f', str(alias_graph)], cwd=root, check=True, capture_output=True)
    # Recreate after both outputs to simulate the atomic transition.
    ml.prepare_projection(inventory, old, common, root/'alias-next', old_aliases=[('.', alias_old)])
    for name in ('first', 'second'):
        (root/name).unlink()
        (root/name).symlink_to(root/'alias-next', target_is_directory=True)
    run = subprocess.run([ninja, '-f', str(alias_graph)], cwd=root, check=True, capture_output=True, text=True)
    assert 'first.o' in run.stdout and 'second.o' in run.stdout, run.stdout
    assert (root/'first.o').read_text() == (root/'second.o').read_text() == 'equal'
    (common/'escape').symlink_to('/etc/passwd')
    try:
        ml.prepare_projection(inventory,old,common,root/'bad')
    except (ValueError, OSError, SDKError):
        assert not (root/'bad').exists()
    else:
        raise AssertionError('escaping symlink accepted')
print('PASS: common ML projection preserves equal timestamps and rejects escaping links')
