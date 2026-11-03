# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the shared GPU patch and make hook.
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
for arg in ('python', 'bmake', 'patch-tool', 'header'):
    p.add_argument('--' + arg, type=Path, required=True)
a = p.parse_args()
if any(not x.is_absolute() for x in vars(a).values()):
    p.error('select absolute tools and original LLVM header')
owner = Path(__file__).resolve().parents[1]
pkgsrc = owner.parents[1]
helper = owner / 'files/apply-profile-gpu-patch.py'
patch = owner / 'patches/patch-13-profile-gpu-bounds'
info = owner / 'distinfo'
fragment = pkgsrc / 'lang/llvm/profile-gpu-patch.mk'
original = a.header.read_bytes()
with tempfile.TemporaryDirectory(prefix='profile-gpu-patch-') as tmp:
    root = Path(tmp)
    patch_copy = root / patch.name
    shutil.copyfile(patch, patch_copy)
    info_copy = root / 'distinfo'
    shutil.copyfile(info, info_copy)
    target = root / 'work/include/llvm/ProfileData/InstrProfData.inc'
    target.parent.mkdir(parents=True)
    target.write_bytes(original)
    cmd = [str(a.python), '-B', str(helper), '--patch-file', str(patch_copy),
           '--distinfo', str(info_copy), '--patch-tool', str(a.patch_tool),
           '--workdir', str(target.parent)]
    def call(command, expected):
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if (result.returncode == 0) != expected:
            raise SystemExit('unexpected command result: ' + result.stdout)
        return result
    text = info_copy.read_text()
    patch_copy.unlink()
    call(cmd, False)
    assert target.read_bytes() == original
    patch_copy.write_bytes(patch.read_bytes())
    info_copy.unlink()
    call(cmd, False)
    assert target.read_bytes() == original
    info_copy.write_text(text)
    info_copy.write_text(text.replace('SHA1 (' + patch.name + ') = ', 'SHA1 (wrong-name) = '))
    call(cmd, False)
    assert target.read_bytes() == original
    info_copy.write_text(text + '\n' + next(line for line in text.splitlines() if patch.name in line) + '\n')
    call(cmd, False)
    assert target.read_bytes() == original
    info_copy.write_text(text)
    patch_copy.write_bytes(patch.read_bytes() + b'\n')
    call(cmd, False)
    assert target.read_bytes() == original
    patch_copy.write_bytes(patch.read_bytes())
    target.unlink()
    call(cmd, False)
    target.write_bytes(original)
    call(cmd, True)
    expected = target.read_bytes()
    assert expected != original and expected.count(b'INSTR_PROF_GPU_SECT(__llvm_profile_data *') == 2
    call(cmd, False)
    assert target.read_bytes() == expected
    print('PASS: checksum missing/duplicate/mismatch, missing target, apply and reapply')
    makefile = root / 'fixture.mk'
    makefile.write_text('.include "' + str(fragment) + '"\n'
                        '.if !target(post-patch)\npost-patch:\n\t@echo reuse-noop\n.endif\n')
    make = [str(a.bmake), '-r', '-f', str(makefile), 'post-patch',
            'PKGSRCDIR=' + str(pkgsrc), 'WRKSRC=' + str(root / 'work'),
            'TOOL_PYTHONBIN=' + str(a.python), 'PATCH=' + str(a.patch_tool)]
    for guard in ('_EMBERBSD_LLVM_REUSE', '_EMBERBSD_LLVM_SHARED_DEVEL'):
        target.write_bytes(original)
        call(make + [guard + '=yes'], True)
        assert target.read_bytes() == original
    target.write_bytes(original)
    call(make, True)
    assert target.read_bytes() == expected
    print('PASS: actual bmake hook and both reuse guards')
