#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise source recomposition and incremental compilation with real Ninja."""
import argparse
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--target', required=True, help='native compiler target triplet')
args = parser.parse_args()
assert args.host_prefix.is_absolute()
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('view', owner / 'electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)


def rejected(call):
    try:
        call()
    except (ValueError, OSError):
        return
    raise AssertionError('invalid refresh unexpectedly succeeded')


def snapshot(path):
    st = path.stat()
    return st.st_ino, st.st_mtime_ns, path.read_bytes()


with tempfile.TemporaryDirectory(prefix='electron-source-refresh-') as temporary:
    root = Path(temporary)
    source = root / 'source'
    (source / 'third_party').mkdir(parents=True)
    (source / '.gn').write_text('fixture')
    (source / 'changed.c').write_text('int changed(void) { return 1; }\n')
    (source / 'stable.c').write_text('int stable(void) { return 2; }\n')
    work = root / 'work'
    work.mkdir()
    destination = work / 'source-view'
    view.create(source, None, destination)
    out = work / 'out'
    out.mkdir()
    cc = shlex.quote(str(args.host_prefix / 'bin/clang'))
    target = shlex.quote(args.target)
    (out / 'build.ninja').write_text(
        f'rule cc\n  command = {cc} --target={target} -c $in -o $out\n'
        'build changed.o: cc ../source-view/src/changed.c\n'
        'build stable.o: cc ../source-view/src/stable.c\n'
        'default changed.o stable.o\n')
    env = os.environ.copy()
    env['PATH'] = str(args.host_prefix / 'bin')
    def ninja():
        subprocess.run([str(args.host_prefix / 'bin/ninja'), '-C', str(out), '-j2'],
                       env=env, check=True, capture_output=True)
    ninja()
    stable = snapshot(out / 'stable.o')
    changed = snapshot(out / 'changed.o')
    source_stable = snapshot(source / 'stable.c')
    # The preparation owner replaces changed files atomically; old hardlinks
    # in the composed view deliberately remain stale until refresh.
    replacement = source / 'replacement'
    replacement.write_text('int changed(void) { return 3; }\n')
    replacement.replace(source / 'changed.c')
    rejected(lambda: view.verify(source, None, destination))
    old = snapshot(destination / 'src/changed.c')
    # A provider/verification failure must not touch the current view or objects.
    with patch.object(view, 'verify', side_effect=ValueError('provider failure')):
        rejected(lambda: view.refresh(source, None, destination))
    assert snapshot(destination / 'src/changed.c') == old
    assert snapshot(out / 'stable.o') == stable
    replace = os.replace
    def fail_install(path, target, **kwargs):
        if Path(path).name == 'new-0':
            raise OSError('injected install failure')
        return replace(path, target, **kwargs)
    with patch.object(view.os, 'replace', fail_install):
        rejected(lambda: view.refresh(source, None, destination))
    assert snapshot(destination / 'src/changed.c') == old
    view.refresh(source, None, destination)
    view.verify(source, None, destination)
    ninja()
    assert snapshot(out / 'stable.o') == stable, 'independent object rebuilt'
    assert snapshot(out / 'changed.o')[2] != changed[2], 'changed source was not rebuilt'
    updated_changed = snapshot(out / 'changed.o')
    ninja()
    assert snapshot(out / 'stable.o') == stable, 'no-op rebuilt stable object'
    assert snapshot(out / 'changed.o') == updated_changed, 'no-op rebuilt changed object'
    assert snapshot(source / 'stable.c') == source_stable
    assert not list(work.glob('.source-view-refresh-*'))
    # Refuse to discard nested build products or a redirected view root.
    product = destination / 'src/out/keep'
    product.write_text('keep')
    rejected(lambda: view.refresh(source, None, destination))
    assert product.read_text() == 'keep'
    product.unlink()
    saved = work / 'saved'
    destination.rename(saved)
    destination.symlink_to(saved, target_is_directory=True)
    rejected(lambda: view.refresh(source, None, destination))
    destination.unlink()
    overlap = root / 'overlap'
    (overlap / 'src/third_party').mkdir(parents=True)
    (overlap / 'src/out').mkdir()
    (overlap / 'src/.gn').write_text('source must survive')
    rejected(lambda: view.refresh(overlap / 'src', None, overlap))
    assert (overlap / 'src/.gn').read_text() == 'source must survive'
    # Recovery if an interruption left the old view renamed away.
    view.refresh(source, None, destination)
    view.verify(source, None, destination)
    assert snapshot(out / 'stable.o') == stable
    # The controller exposes refresh only through reconfigure; normal builds
    # continue verifying their source view instead of silently replacing it.
    spec = importlib.util.spec_from_file_location(
        'controller', owner / 'electron44/files/build-electron.py')
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    options = argparse.Namespace(work=work, workspace=root, host_prefix=args.host_prefix,
                                 node_source=root / 'node', phase='reconfigure',
                                 refresh_source_view=True)
    with patch.object(controller, 'local_module', return_value=view):
        with patch.object(view, 'refresh', return_value=destination / 'src') as called:
            assert controller.gn_source(options) == destination / 'src'
            called.assert_called_once()
        options.phase = 'build'
        with patch.object(view, 'refresh') as called:
            rejected(lambda: controller.gn_source(options))
            called.assert_not_called()
        options.refresh_source_view = False
        with patch.object(view, 'verify', return_value=destination / 'src') as called:
            assert controller.gn_source(options) == destination / 'src'
            called.assert_called_once()
print('PASS: incremental rebuild, retained object, failure rollback, output protection and recovery')
