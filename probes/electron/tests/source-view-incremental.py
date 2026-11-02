#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise incremental source view behavior with isolated real files."""
import importlib.util
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

owner = Path(__file__).resolve().parents[1] / 'electron44/files/protobuf-source-view.py'
spec = importlib.util.spec_from_file_location('view', owner)
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)

def snap(path):
    st = path.stat()
    return st.st_ino, st.st_mtime_ns, path.read_bytes()

with tempfile.TemporaryDirectory(prefix='incremental-view-root-') as temporary:
    root = Path(temporary)
    source = root / 'source'
    (source / 'third_party').mkdir(parents=True)
    (source / '.gn').write_text('fixture')
    for name in ('a', 'b', 'stable'):
        (source / name).write_text(name)
    destination = root / 'view'
    view.create(source, None, destination)
    stable = snap(destination / 'src/stable')
    root_inode = (destination / 'src').stat().st_ino
    for name in ('a', 'b'):
        replacement = source / (name + '.new')
        replacement.write_text(name + '2')
        replacement.replace(source / name)
    old = [snap(destination / 'src' / name) for name in ('a', 'b')]
    replace = os.replace
    def fail_install(src, dst, **kwargs):
        if Path(src).name == 'new-1':
            raise OSError('injected second install failure')
        return replace(src, dst, **kwargs)
    with patch.object(view.os, 'replace', fail_install):
        try:
            view.refresh(source, None, destination)
        except OSError:
            pass
        else:
            raise AssertionError('injected failure did not fire')
    assert [snap(destination / 'src' / name) for name in ('a', 'b')] == old
    view.refresh(source, None, destination)
    view.verify(source, None, destination)
    assert snap(destination / 'src/stable') == stable
    assert (destination / 'src').stat().st_ino == root_inode
    before = snap(destination / 'src/a')
    replacement = source / 'replacement'
    replacement.write_bytes((source / 'a').read_bytes())
    replacement.replace(source / 'a')
    view.refresh(source, None, destination)
    assert snap(destination / 'src/a') == before
    view._refresh_marker(destination).write_text('source-view-leaves-v1\n')
    try:
        view.verify(source, None, destination)
    except ValueError:
        pass
    else:
        raise AssertionError('incomplete update was accepted')
    view.refresh(source, None, destination)
    view.verify(source, None, destination)
    assert not view._refresh_marker(destination).exists()
print('PASS: leaf delta, rollback, unchanged inode/mtime, equal bytes, marker recovery')

# Provider-only changes, interrupted refresh and structural fallback.
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / 'source'
    (source / 'third_party').mkdir(parents=True)
    (source / '.gn').write_text('fixture')
    for name in ('a', 'b'):
        (source / name).write_text(name)
    for name in ('node-old', 'node-new'):
        (root / name).mkdir()
        (root / name / 'node.gni').write_text('fixture')
    for name in ('v8-old', 'v8-new'):
        (root / name / 'include').mkdir(parents=True)
        (root / name / 'BUILD.gn').write_text('fixture')
        (root / name / 'include/v8-version.h').write_text('fixture')
    destination = root / 'view'
    view.create(source, None, destination, node=root / 'node-old', v8=root / 'v8-old')
    stable = snap(destination / 'src/a')
    root_inode = (destination / 'src').stat().st_ino
    providers = dict(node=root / 'node-new', v8=root / 'v8-new')
    view.refresh(source, None, destination, **providers)
    view.verify(source, None, destination, **providers)
    assert os.readlink(destination / 'src/v8') == str((root / 'v8-new').resolve())
    assert os.readlink(destination / 'src/third_party/electron_node') == str((root / 'node-new').resolve())
    assert snap(destination / 'src/a') == stable
    assert (destination / 'src').stat().st_ino == root_inode
    view.refresh(source, None, destination, **providers)
    assert snap(destination / 'src/a') == stable
    assert (destination / 'src').stat().st_ino == root_inode

    for name in ('a', 'b'):
        replacement = source / (name + '-new')
        replacement.write_text(name + '2')
        replacement.replace(source / name)
    # Model a process interruption after one leaf was installed.
    (destination / 'src/a').unlink()
    (destination / 'src/a').write_text('a2')
    marker = view._refresh_marker(destination)
    marker.write_text('source-view-leaves-v1\n')
    try:
        view.verify(source, None, destination, **providers)
    except ValueError:
        pass
    else:
        raise AssertionError('incomplete update was accepted')
    view.refresh(source, None, destination, **providers)
    view.verify(source, None, destination, **providers)
    assert (destination / 'src/a').read_text() == 'a2'
    assert (destination / 'src/b').read_text() == 'b2'
    assert not marker.exists()

    marker.write_text('invalid')
    (source / 'new').write_text('new')
    try:
        view.refresh(source, None, destination, **providers)
    except ValueError:
        pass
    else:
        raise AssertionError('malformed marker was accepted')
    assert not (destination / 'src/new').exists()
    marker.unlink()
    view.refresh(source, None, destination, **providers)
    assert (destination / 'src/new').read_text() == 'new'
    os.chmod(source / 'a', 0o600)
    view.refresh(source, None, destination, **providers)
    assert stat.S_IMODE((destination / 'src/a').stat().st_mode) == 0o600

# Multiple names sharing one old inode must both be refreshed.
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / 'source'
    (source / 'third_party').mkdir(parents=True)
    (source / '.gn').write_text('fixture')
    (source / 'a').write_text('old')
    os.link(source / 'a', source / 'b')
    destination = root / 'view'
    view.create(source, None, destination)
    for name in ('a', 'b'):
        replacement = source / (name + '.new')
        replacement.write_text('new' + name)
        replacement.replace(source / name)
    view.refresh(source, None, destination)
    view.verify(source, None, destination)
    assert (destination / 'src/a').read_text() == 'newa'
    assert (destination / 'src/b').read_text() == 'newb'

# Redirected parents cannot redirect rollback into another directory.
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / 'source'
    (source / 'third_party').mkdir(parents=True)
    (source / 'sub').mkdir()
    (source / '.gn').write_text('fixture')
    for name in ('a', 'b'):
        (source / 'sub' / name).write_text(name)
    destination = root / 'view'
    view.create(source, None, destination)
    for name in ('a', 'b'):
        replacement = source / 'sub' / (name + '.new')
        replacement.write_text(name + '2')
        replacement.replace(source / 'sub' / name)
    outside = root / 'outside'
    outside.mkdir()
    for name in ('a', 'b'):
        (outside / name).write_text('outside')
    replace = os.replace

    def redirect_parent(src, dst, **kwargs):
        result = replace(src, dst, **kwargs)
        if Path(src).name == 'new-0':
            (destination / 'src/sub').rename(destination / 'src/moved')
            (destination / 'src/sub').symlink_to(outside, target_is_directory=True)
        return result

    try:
        with patch.object(view.os, 'replace', redirect_parent):
            view.refresh(source, None, destination)
    except ValueError:
        pass
    else:
        raise AssertionError('parent redirect was accepted')
    assert (outside / 'a').read_text() == 'outside'
    assert (outside / 'b').read_text() == 'outside'
    assert view._refresh_marker(destination).exists()


# Invalid provider must be rejected before the old view changes.
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / 'source'
    (source / 'third_party').mkdir(parents=True)
    (source / '.gn').write_text('fixture')
    old_v8 = root / 'v8-old'
    (old_v8 / 'include').mkdir(parents=True)
    (old_v8 / 'BUILD.gn').write_text('fixture')
    (old_v8 / 'include/v8-version.h').write_text('fixture')
    bad_v8 = root / 'v8-invalid'
    bad_v8.mkdir()
    destination = root / 'view'
    view.create(source, None, destination, v8=old_v8)
    before = os.readlink(destination / 'src/v8')
    try:
        view.refresh(source, None, destination, v8=bad_v8)
    except ValueError:
        pass
    else:
        raise AssertionError('incomplete V8 provider was accepted')
    assert os.readlink(destination / 'src/v8') == before
