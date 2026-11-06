#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise verified, no-replace incremental directory publication."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument('--owner', type=Path, default=Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/protobuf-source-view.py')
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--vulkan-build', type=Path, required=True)
a = parser.parse_args()
sys.path.insert(0, str(a.sdk_source.resolve(strict=True) / 'src'))
from emberbsd_sdk import publication
spec = importlib.util.spec_from_file_location('view', a.owner)
view = importlib.util.module_from_spec(spec); spec.loader.exec_module(view)

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def refuse(fn):
    try: fn()
    except (ValueError, OSError): return
    raise AssertionError('unverified directory accepted')

with tempfile.TemporaryDirectory(prefix='source-view-created-dirs-') as tmp:
    root = Path(tmp).resolve(); source = root / 'source'; dest = root / 'view'
    source.mkdir(); dest.mkdir(); (source / 'keep').write_text('unchanged')
    view.mirror(source, dest / 'src')
    keep = dest / 'src/keep'; before = (keep.stat().st_ino, keep.stat().st_mtime_ns)
    vulkan = source / 'emberbsd_vulkan'; vulkan.mkdir()
    shutil.copy2(a.vulkan_build.resolve(strict=True), vulkan / 'BUILD.gn')
    created = {str((vulkan / 'BUILD.gn').resolve()): digest(vulkan / 'BUILD.gn')}
    def verify(source, protobuf, destination, *, _updates, _refresh, _created_files=None, **kwargs):
        view.mirror(source, destination / 'src', verify=True, updates=_updates, created_files=_created_files)
    view.verify = verify
    def refresh(mapping=created, publisher=publication):
        return view._refresh_leaves(source, None, dest, {}, created_files=mapping, publication=publisher)
    refuse(lambda: refresh({}))
    wrong = dict(created); wrong[next(iter(wrong))] = '0' * 64
    refuse(lambda: refresh(wrong))
    (vulkan / 'unknown').write_text('foreign')
    refuse(refresh); (vulkan / 'unknown').unlink()
    (vulkan / 'symlink').symlink_to(vulkan / 'BUILD.gn')
    refuse(refresh); (vulkan / 'symlink').unlink()
    (source / 'empty').mkdir(); refuse(refresh); (source / 'empty').rmdir()
    refresh()
    assert (dest / 'src/emberbsd_vulkan/BUILD.gn').read_bytes() == (vulkan / 'BUILD.gn').read_bytes()
    assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == before
    # Two new subtrees: the second publish fails; the first must roll back.
    for name in ('first', 'second'):
        (source / name).mkdir(); (source / name / 'BUILD.gn').write_text(name)
        created[str((source / name / 'BUILD.gn').resolve())] = digest(source / name / 'BUILD.gn')
    calls = []
    def fail_second(src, dst):
        calls.append(dst)
        if len(calls) == 2: raise OSError('second publication failure')
        return publication.publish_directory_noreplace(src, dst)
    refuse(lambda: refresh(publisher=SimpleNamespace(publish_directory_noreplace=fail_second)))
    assert len(calls) == 2
    assert not (dest / 'src/first').exists() and not (dest / 'src/second').exists()
    assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == before
    # A marker and an already-published verified subtree model interrupted retry.
    shutil.copytree(source / 'first', dest / 'src/first')
    marker = view._refresh_marker(dest); marker.write_text('source-view-leaves-v1\n')
    refresh(); assert not marker.exists() and (dest / 'src/second/BUILD.gn').read_text() == 'second'
    foreign_child = dest / 'src/first/foreign'; foreign_child.write_text('foreign')
    refuse(refresh); assert foreign_child.read_text() == 'foreign'; foreign_child.unlink()
    mutation = source / 'mutation'; mutation.mkdir(); mutation_file = mutation / 'BUILD.gn'
    mutation_file.write_text('original')
    created[str(mutation_file.resolve())] = digest(mutation_file)
    def mutate_source(src, dst):
        publication.publish_directory_noreplace(src, dst)
        mutation_file.write_text('changed')
    refuse(lambda: refresh(publisher=SimpleNamespace(publish_directory_noreplace=mutate_source)))
    assert not (dest / 'src/mutation').exists()
    mutation_file.write_text('original'); refresh()
    # Do not remove a foreign child that appeared after an earlier publication.
    for name in ('fourth', 'fifth'):
        (source / name).mkdir(); (source / name / 'BUILD.gn').write_text(name)
        created[str((source / name / 'BUILD.gn').resolve())] = digest(source / name / 'BUILD.gn')
    published = []
    def foreign_during_rollback(src, dst):
        if published:
            (Path(published[0]) / 'foreign').write_text('foreign')
            raise OSError('second publication interrupted')
        publication.publish_directory_noreplace(src, dst); published.append(dst)
    refuse(lambda: refresh(publisher=SimpleNamespace(publish_directory_noreplace=foreign_during_rollback)))
    assert (Path(published[0]) / 'foreign').read_text() == 'foreign'
    assert marker.exists()
    (Path(published[0]) / 'foreign').unlink(); refresh(); assert not marker.exists()
    # A competing foreign directory must not be replaced by the no-replace publication.
    third = source / 'third'; third.mkdir(); (third / 'BUILD.gn').write_text('third')
    created[str((third / 'BUILD.gn').resolve())] = digest(third / 'BUILD.gn')
    def race(src, dst):
        Path(dst).mkdir(); (Path(dst) / 'foreign').write_text('foreign')
        return publication.publish_directory_noreplace(src, dst)
    refuse(lambda: refresh(publisher=SimpleNamespace(publish_directory_noreplace=race)))
    assert (dest / 'src/third/foreign').read_text() == 'foreign'
    assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == before
print('PASS: verified Vulkan directory, rollback, retry, no-replace and foreign input rejection')
