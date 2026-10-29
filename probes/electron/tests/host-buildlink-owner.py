#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise real pkgsrc host buildlink selection and stale inputs."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'pkgsrc', 'host-prefix', 'stage-root', 'base-makeconf',
             'binding-record', 'bmake-mk', 'lock-root', 'work-parent'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
owner = Path(__file__).resolve().parents[1] / 'electron44'
with tempfile.TemporaryDirectory(prefix='electron-host-buildlink-owner-', dir=a.work_parent) as temp:
    root = Path(temp)
    local = root / 'consumer/files'; local.mkdir(parents=True)
    shutil.copy2(owner / 'files/host-buildlink.py', local / 'host-buildlink.py')
    shutil.copytree(owner / 'files/host-buildlink', local / 'host-buildlink')
    deps = local.parent / 'host-dependencies.mk'; shutil.copy2(owner / 'host-dependencies.mk', deps)
    def command(work):
        return [sys.executable, '-B', str(local / 'host-buildlink.py'),
                '--sdk-source', str(a.sdk_source), '--pkgsrc-root', str(a.pkgsrc),
                '--host-prefix', str(a.host_prefix), '--stage-root', str(a.stage_root),
                '--base-makeconf', str(a.base_makeconf), '--binding-record', str(a.binding_record),
                '--bmake-mk', str(a.bmake_mk), '--work', str(work), '--lock-root', str(a.lock_root)]
    def run(argv, expected=0):
        result = subprocess.run(argv, text=True, capture_output=True)
        assert result.returncode == expected, (result.returncode, result.stderr)
        return result.stdout.strip()
    first = root / 'first'; view = Path(run(command(first)))
    assert (view / 'lib/pkgconfig/protobuf.pc').is_file()
    assert run(command(first) + ['--check']) == str(view)
    deps.write_text(deps.read_text() + '\n# changed declaration\n')
    run(command(first) + ['--check'], 3)
    second = root / 'second'; view = Path(run(command(second)))
    link = view / 'lib/pkgconfig/protobuf.pc'; link.unlink()
    run(command(second) + ['--check'], 3)
    third = root / 'third'; view = Path(run(command(third)))
    local_archive = view / 'lib/libffi.la'
    assert local_archive.is_file() and not local_archive.is_symlink()
    local_archive.write_text(local_archive.read_text() + '\n# changed local view\n')
    run(command(third) + ['--check'], 3)
    fourth = root / 'fourth'; view = Path(run(command(fourth)))
    (view / 'directory-link').symlink_to(view / 'include', target_is_directory=True)
    result = subprocess.run(command(fourth) + ['--check'], capture_output=True, text=True)
    assert result.returncode != 0 and 'directory symlinks are unsupported' in result.stderr
    deps.write_text(deps.read_text() + '\nDEPENDS+= electron-missing-provider>=1:../../devel/zlib\n')
    result = subprocess.run(command(root / 'missing'), capture_output=True, text=True)
    assert result.returncode != 0
print('PASS: host buildlink selection, stale inputs and missing dependency')
