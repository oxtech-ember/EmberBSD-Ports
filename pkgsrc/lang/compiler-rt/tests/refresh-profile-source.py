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

# A completed transition may be followed by the next verified transition.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); before = root / "before"; after = root / "after"; work = root / "work"
    for path in (before, after, work): path.mkdir()
    name = "compiler-rt/lib/profile/InstrProfilingFile.c"
    put(before, name, b"middle"); put(after, name, b"new")
    dest = put(work / "llvm-project-23.1.4.src", name, b"middle")
    put(work, ".extract_done", b"compiler-rt-23.1.4nb11\n")
    put(work, ".configure_done", b"compiler-rt-23.1.4nb12\n")
    put(work, ".patch_done", b"historical")
    old = dict(version="23.1.4", before="old", after="middle-id", package="compiler-rt-23.1.4nb12", package_kind="compiler-rt", paths=[name], state="complete")
    next_identity = dict(version="23.1.4", before="middle-id", after="new-id", package="compiler-rt-23.1.4nb13")
    receipt = work / m.RECEIPT
    for bad in (dict(old, state="pending"), dict(old, after="foreign")):
        receipt.write_text(json.dumps(bad))
        rejected(lambda: m.apply_files(before, after, work, "compiler-rt", {name}, next_identity))
        assert dest.read_bytes() == b"middle"
    receipt.write_text(json.dumps(old)); (work/".configure_done").write_text("compiler-rt-23.1.4nb10\n")
    rejected(lambda: m.apply_files(before, after, work, "compiler-rt", {name}, next_identity))
    (work/".configure_done").write_text("compiler-rt-23.1.4nb12\n")
    second = "compiler-rt/lib/profile/InstrProfilingValue.c"
    put(before, second, b"middle2"); put(after, second, b"new2")
    second_dest = put(work / "llvm-project-23.1.4.src", second, b"middle2")
    original_atomic = m.atomic
    def interrupted_chain(path, data, mode=0o644):
        if path == second_dest:
            raise OSError("interrupted after first file")
        return original_atomic(path, data, mode)
    m.atomic = interrupted_chain
    rejected(lambda: m.apply_files(before, after, work, "compiler-rt", {name, second}, next_identity))
    m.atomic = original_atomic
    saved = json.loads(receipt.read_text())
    assert saved["state"] == "pending" and saved["configured_before"] == "compiler-rt-23.1.4nb12"
    assert dest.read_bytes() == b"new" and second_dest.read_bytes() == b"middle2"
    wrong = dict(saved, configured_before="invalid")
    receipt.write_text(json.dumps(wrong))
    rejected(lambda: m.apply_files(before, after, work, "compiler-rt", {name, second}, next_identity))
    receipt.write_text(json.dumps(saved))
    for wrong_cookie in ("compiler-rt-23.1.4nb10\n", "compiler-rt-23.1.4nb11\n"):
        (work/".configure_done").write_text(wrong_cookie)
        rejected(lambda: m.apply_files(before, after, work, "compiler-rt", {name, second}, next_identity))
    (work/".configure_done").write_text("compiler-rt-23.1.4nb12\n")
    assert m.apply_files(before, after, work, "compiler-rt", {name, second}, next_identity) == 1
    assert second_dest.read_bytes() == b"new2" and json.loads(receipt.read_text())["after"] == "new-id"
    assert m.apply_files(before, after, work, "compiler-rt", {name, second}, next_identity, check=True) == 0
    assert m.apply_files(before, after, work, "compiler-rt", {name, second}, next_identity) == 0
    (work/".configure_done").write_text("compiler-rt-23.1.4nb13\n")
    assert m.apply_files(before, after, work, "compiler-rt", {name, second}, next_identity, check=True) == 0
    assert m.apply_files(before, after, work, "compiler-rt", {name, second}, next_identity) == 0
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
    # Exported v2 has no revision: verify current blobs and reconstruct old distinfo.
    exported = dict(before, version=2, recipe=dict(before["recipe"], ports_revision=None))
    def current_git_result(argv, input, **kwargs):
        blobs = {m.DIST:new_dist, "pkgsrc/lang/llvm/version.mk":b"version"}
        out = b""
        for row in input.splitlines():
            name = row.decode().split(":", 1)[1]; data = blobs[name]
            out += b"0" * 40 + b" blob " + str(len(data)).encode() + b"\n" + data + b"\n"
        return types.SimpleNamespace(stdout=out)
    m.subprocess.run = current_git_result
    (root/"patches/patch-profile").write_bytes(patch)
    assert m.selected_delta(exported, current, "/git") == {"compiler-rt/lib/profile/example.c"}
    forged = dict(exported, recipe=dict(exported["recipe"], files=dict(prior_files, **{m.DIST:digest(b"forged")})))
    rejected(lambda: m.selected_delta(forged, current, "/git"))
    forged = dict(exported, recipe=dict(exported["recipe"], files=dict(prior_files, **{"pkgsrc/lang/llvm/version.mk":digest(b"forged")})))
    rejected(lambda: m.selected_delta(forged, current, "/git"))
    m.owner.OWNER=old_owner; m.owner.PORTS=old_ports; m.subprocess.run=old_run
print('profile patch provenance and refusals: PASS')

# Only unchanged, byte-identical patch candidates may receive old mtimes.
import os
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); a=root/'old'; b=root/'new'; a.mkdir(); b.mkdir()
    names={'compiler-rt/lib/builtins/one.c','compiler-rt/lib/builtins/two.h'}
    for i,name in enumerate(sorted(names)):
        x=put(a,name,('same'+str(i)).encode()); y=put(b,name,('same'+str(i)).encode())
        os.utime(x,ns=(1000000000+i,1000000000+i));os.utime(y,ns=(2000000000+i,2000000000+i))
    plan=m.mtime_plan(a,b,names)
    first, second = sorted(names)
    first_mtime = (b/first).stat().st_mtime_ns
    (b/second).write_bytes(b'mutated after planning')
    rejected(lambda: m.preserve_mtimes(a,b,plan))
    assert (b/first).stat().st_mtime_ns == first_mtime
    (b/second).write_bytes((a/second).read_bytes())
    os.utime(b/second,ns=(2000000001,2000000001))
    plan=m.mtime_plan(a,b,names)
    assert m.preserve_mtimes(a,b,plan)==2
    for name in names:
        assert (a/name).stat().st_mtime_ns==(b/name).stat().st_mtime_ns
    n=sorted(names)[1];os.utime(b/n,ns=(3000000000,3000000000));(b/n).write_bytes(b'changed')
    untouched=(b/sorted(names)[0]).stat().st_mtime_ns
    rejected(lambda:m.mtime_plan(a,b,names))
    assert (b/sorted(names)[0]).stat().st_mtime_ns==untouched
    (b/n).unlink(); os.link(a/n,b/n)
    rejected(lambda:m.mtime_plan(a,b,names))
print('patched source timestamps, mismatch and aliases: PASS')
