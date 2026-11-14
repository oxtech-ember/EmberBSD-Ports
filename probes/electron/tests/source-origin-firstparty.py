#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise source-origin first-party reuse with the selected Ninja."""
import importlib.util
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('view', owner / '../../pkgsrc/devel/electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)
parser = argparse.ArgumentParser()
parser.add_argument('--ninja', type=Path, required=True)
ninja = parser.parse_args().ninja
assert ninja.is_absolute()
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp).resolve()
    old, new, old_view, candidate = (root / name for name in ('old', 'new', 'view', 'candidate'))
    for tree in (old, new):
        (tree / 'base').mkdir(parents=True)
        (tree / '.git').mkdir()
        (tree / 'third_party').mkdir()
        (tree / '.gn').write_text('fixture')
        (tree / '.git' / 'metadata').write_text('git')
        for name in ('stable', 'changed', 'mode', 'created'):
            (tree / 'base' / name).write_text(name)
    (new / 'base/changed').write_text('different')
    (new / 'base/mode').chmod(0o755)
    view.create(old, None, old_view)
    out = root / 'out'
    out.mkdir()
    command = shlex.quote(sys.executable) + ' -c ' + shlex.quote('import pathlib,sys; pathlib.Path(sys.argv[2]).write_text(pathlib.Path(sys.argv[1]).read_text())') + ' $in $out'
    def graph(command):
        (out / 'build.ninja').write_text('rule copy\n  command = ' + command + '\n' + ''.join('build ' + name + '.o: copy ../view/src/base/' + name + '\n' for name in ('stable', 'changed', 'mode')))
    def run():
        return subprocess.run([str(ninja), '-C', str(out)], check=True, capture_output=True, text=True).stdout
    graph(command)
    run()
    object_before = (out / 'stable.o').stat().st_mtime_ns
    time.sleep(0.03)
    # Give changed inputs new actual mtimes; never touch outputs or Ninja logs.
    for name in ('changed', 'mode'):
        path = new / 'base' / name
        os.utime(path, None)
    view.create(new, None, candidate, previous_view=old_view,
                created_files={str(new / 'base/created'): '0' * 64})
    assert (candidate / 'src/base/stable').stat().st_ino == (old_view / 'src/base/stable').stat().st_ino
    for name in ('changed', 'mode', 'created'):
        assert (candidate / 'src/base' / name).stat().st_ino != (old_view / 'src/base' / name).stat().st_ino
    assert (candidate / 'src/.git/metadata').stat().st_ino != (old_view / 'src/.git/metadata').stat().st_ino
    view.verify(new, None, candidate)
    old_view.rename(root / 'retired')
    candidate.rename(old_view)
    result = run()
    assert 'changed.o' in result and 'mode.o' in result and 'stable.o' not in result, result
    assert (out / 'stable.o').stat().st_mtime_ns == object_before
    graph(command + ' ')
    assert 'stable.o' in run(), 'changed command must rebuild'
    # EXDEV fallback preserves verified bytes and mtime, without sharing inode.
    oldfile, newfile = root / 'retired/src/base/stable', new / 'base/stable'
    copied = root / 'copied'
    def exdev(*args, **kwargs):
        import errno
        raise OSError(errno.EXDEV, 'fixture')
    with patch.object(view.os, 'link', exdev):
        assert view._reuse_firstparty(newfile, oldfile, copied)
    assert copied.read_bytes() == oldfile.read_bytes() and copied.stat().st_mtime_ns == oldfile.stat().st_mtime_ns
    assert copied.stat().st_ino != oldfile.stat().st_ino
    # A redirected ancestor cannot be used to choose an old file.
    alias = root / 'alias'
    alias.symlink_to(oldfile.parent, target_is_directory=True)
    try:
        view._reuse_firstparty(newfile, alias / 'stable', root / 'redirected')
    except OSError:
        pass
    else:
        raise AssertionError('symlink ancestor accepted')
    assert not (root / 'redirected').exists()
    # A different inode substituted between comparison and link is rejected;
    # only the candidate leaf just created by the helper is removed.
    target = root / 'bad-link'
    real_link = os.link
    def substitute(source, destination, **kwargs):
        return real_link(str(newfile), destination, dst_dir_fd=kwargs['dst_dir_fd'])
    with patch.object(view.os, 'link', substitute):
        try:
            view._reuse_firstparty(newfile, oldfile, target)
        except ValueError:
            pass
        else:
            raise AssertionError('link substitution accepted')
    assert target.stat().st_ino == newfile.stat().st_ino
    target.unlink()
    # Replace the owned link after creation but before its first stat.  The
    # foreign name must survive the helper's exception cleanup.
    foreign = root / 'foreign'
    foreign.write_bytes(oldfile.read_bytes())
    swapped = root / 'swapped'
    def swap_after_link(source, destination, **kwargs):
        real_link(source, destination, **kwargs)
        os.unlink(destination, dir_fd=kwargs['dst_dir_fd'])
        real_link(str(foreign), destination, dst_dir_fd=kwargs['dst_dir_fd'])
    with patch.object(view.os, 'link', swap_after_link):
        try:
            view._reuse_firstparty(newfile, oldfile, swapped)
        except ValueError:
            pass
        else:
            raise AssertionError('post-link replacement accepted')
    assert swapped.stat().st_ino == foreign.stat().st_ino
    # Replacing the EXDEV copy with byte-equal content before reopening must
    # be rejected by inode identity and the foreign file retained.
    copied_foreign = root / 'copy-replaced'
    real_open = os.open
    def swap_copy(path, flags, *args, **kwargs):
        if path == copied_foreign.name and flags == (os.O_RDONLY | os.O_NOFOLLOW):
            os.unlink(path, dir_fd=kwargs['dir_fd'])
            real_link(str(foreign), path, dst_dir_fd=kwargs['dir_fd'])
        return real_open(path, flags, *args, **kwargs)
    with patch.object(view.os, 'link', exdev), patch.object(view.os, 'open', swap_copy):
        try:
            view._reuse_firstparty(newfile, oldfile, copied_foreign)
        except ValueError:
            pass
        else:
            raise AssertionError('byte-equal foreign copy accepted')
    assert copied_foreign.stat().st_ino == foreign.stat().st_ino
    # Two prepared origins may already share an inode.  Normal mirror keeps
    # that inode without invalidating a ctime check on a new hard link.
    shared = root / 'shared'
    os.link(oldfile, shared)
    assert not view._reuse_firstparty(shared, oldfile, root / 'same-inode')
    assert not (root / 'same-inode').exists()
    # A change between lstat and open is refused even when bytes are equal.
    old_race = root / 'old-race'
    old_race.write_bytes(oldfile.read_bytes())
    def swap_old(path, flags, *args, **kwargs):
        if path == old_race.name and flags == (os.O_RDONLY | os.O_NOFOLLOW):
            os.unlink(path, dir_fd=kwargs['dir_fd'])
            real_link(str(foreign), path, dst_dir_fd=kwargs['dir_fd'])
        return real_open(path, flags, *args, **kwargs)
    with patch.object(view.os, 'open', swap_old):
        try:
            view._reuse_firstparty(newfile, old_race, root / 'old-race-out')
        except ValueError:
            pass
        else:
            raise AssertionError('pre-open replacement accepted')
    assert not (root / 'old-race-out').exists()
print('first-party source-origin Ninja: PASS')
