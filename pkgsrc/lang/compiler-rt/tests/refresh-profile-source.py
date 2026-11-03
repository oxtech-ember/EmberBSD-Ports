#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Focused source refresh, retry, path and refusal tests."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

files = Path(__file__).resolve().parents[1] / 'files'
sys.path.insert(0, str(files))
spec = importlib.util.spec_from_file_location('refresh_profile', files / 'refresh-profile-source.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
identity = dict(version='23.1.4', before='before', after='after', package='compiler-rt-23.1.4nb12')

def put(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path

def rejected(fn):
    try:
        fn()
    except (ValueError, OSError):
        return
    raise AssertionError('expected refusal')

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); before = root/'before'; after = root/'after'; work = root/'work'
    for p in (before, after, work): p.mkdir()
    name = 'compiler-rt/lib/profile/InstrProfilingValue.c'
    header = m.HEADER
    targetroot = work/'llvm-project-23.1.4.src'
    for path, old, new in ((name, b'old', b'new'), (header, b'header', b'new header')):
        put(before, path, old); put(after, path, new); put(targetroot, path, old)
    for cookie in ('.extract_done', '.configure_done'):
        put(work, cookie, b'compiler-rt-23.1.4nb11\n')
    put(work, '.patch_done', b'historical\n')
    put(work, '.build_done', b'old')
    rejected(lambda: m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity))
    assert m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity, check=True) == 2
    assert not (work/m.RECEIPT).exists()
    (work/'.build_done').unlink()
    assert m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity) == 2
    saved = (targetroot/name).stat().st_mtime_ns
    assert m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity) == 0
    assert (targetroot/name).stat().st_mtime_ns == saved
    assert json.loads((work/m.RECEIPT).read_text())['state'] == 'complete'
    # A new configure followed by a failed build keeps the old extract cookie.
    (work/'.configure_done').write_text('compiler-rt-23.1.4nb12\n')
    assert m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity, check=True) == 0
    assert m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity) == 0
    (work/'.configure_done').unlink()
    receipt_mtime = (work/m.RECEIPT).stat().st_mtime_ns
    assert m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity, check=True) == 0
    assert m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity) == 0
    assert (work/m.RECEIPT).stat().st_mtime_ns == receipt_mtime
    rejected(lambda: m.regular(before, '/etc/passwd'))
    (targetroot/name).write_bytes(b'other')
    rejected(lambda: m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity))
    assert (targetroot/header).read_bytes() == b'new header'
    (targetroot/name).unlink(); (targetroot/name).symlink_to(after/name)
    rejected(lambda: m.apply_files(before, after, work, 'compiler-rt', {name, header}, identity))

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); before=root/'before'; after=root/'after'; work=root/'work'
    for p in (before, after, work): p.mkdir()
    put(before,m.HEADER,b'old'); put(after,m.HEADER,b'new')
    dst=put(work/'llvm-project-23.1.4.src','llvm/include/llvm/ProfileData/InstrProfData.inc',b'old')
    for cookie in ('.extract_done', '.configure_done'):
        put(work, cookie, b'llvm-23.1.4nb6\n')
    put(work, '.patch_done', b'historical\n')
    identity = dict(identity, package='llvm-23.1.4nb7')
    original=m.atomic
    def interrupted(path, data, mode=0o644):
        if path == dst: raise OSError('simulated interruption')
        return original(path,data,mode)
    m.atomic=interrupted
    rejected(lambda: m.apply_files(before,after,work,'llvm',{m.HEADER},identity))
    assert json.loads((work/m.RECEIPT).read_text())['state'] == 'pending'
    (work/'.configure_done').unlink()
    rejected(lambda: m.apply_files(before,after,work,'llvm',{m.HEADER},identity,check=True))
    (work/'.configure_done').write_text('llvm-23.1.4nb6\n')
    m.atomic=original
    assert m.apply_files(before,after,work,'llvm',{m.HEADER},identity) == 1
    assert dst.read_bytes() == b'new'
print('profile source refresh and recovery: PASS')

# Verify complete historical input blobs, add-only changes and patch paths.
import hashlib
import types
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); (root/'patches').mkdir()
    old_dist = b'SHA512 (llvm.tar.xz) = fixed\n'
    new_dist = old_dist + b'SHA1 (patch-profile) = checked\n'
    patch = (b'--- a/compiler-rt/lib/profile/example.c\n'
             b'+++ b/compiler-rt/lib/profile/example.c\n@@ -1 +1 @@\n-old\n+new\n')
    (root/'distinfo').write_bytes(new_dist); (root/'patches/patch-profile').write_bytes(patch)
    digest=lambda b: hashlib.sha256(b).hexdigest()
    prior_files = {m.DIST:digest(old_dist), 'pkgsrc/lang/llvm/version.mk':digest(b'version')}
    before={'format':'emberbsd-llvm-source','version':1,'llvm_version':'23.1.4',
            'components':['compiler-rt'],'source':{'archive':'same'},
            'recipe':{'ports_revision':'a'*40,'files':prior_files}}
    current=dict(before,recipe={'files':dict(prior_files,**{m.DIST:digest(new_dist),
                  m.PATCH+'patch-profile':digest(patch)})})
    old_owner, old_ports, old_run = m.owner.OWNER, m.owner.PORTS, m.subprocess.run
    m.owner.OWNER=root; m.owner.PORTS=root
    def git_result(argv, input, **kwargs):
        blobs={m.DIST:old_dist,'pkgsrc/lang/llvm/version.mk':b'version'}; out=b''
        for row in input.splitlines():
            name=row.decode().split(':',1)[1]; data=blobs[name]
            out+=b'0'*40+b' blob '+str(len(data)).encode()+b'\n'+data+b'\n'
        return types.SimpleNamespace(stdout=out)
    m.subprocess.run=git_result
    assert m.selected_delta(before,current,'/git') == {'compiler-rt/lib/profile/example.c'}
    bad=dict(current,source={'archive':'other'})
    rejected(lambda: m.selected_delta(before,bad,'/git'))
    bad=dict(current,recipe={'files':dict(current['recipe']['files'], **{'pkgsrc/lang/llvm/version.mk':'bad'})})
    rejected(lambda: m.selected_delta(before,bad,'/git'))
    unsafe = patch + patch.replace(b'lib/profile',b'lib/builtins')
    (root/'patches/patch-profile').write_bytes(unsafe)
    bad = dict(current, recipe={'files':dict(current['recipe']['files'],
                **{m.PATCH+'patch-profile':digest(unsafe)})})
    rejected(lambda: m.selected_delta(before,bad,'/git'))
    bad_before = dict(before, recipe=dict(before['recipe'],
        files=dict(before['recipe']['files'], **{'pkgsrc/lang/llvm/version.mk':'bad'})))
    rejected(lambda: m.selected_delta(bad_before,current,'/git'))
    m.owner.OWNER=old_owner; m.owner.PORTS=old_ports; m.subprocess.run=old_run
print('profile patch provenance and refusals: PASS')
