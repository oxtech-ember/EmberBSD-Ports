#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
"""Check target context generation from an installed Perl Config."""
import argparse
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('host-perl', 'target-config', 'sysroot', 'cc', 'ld', 'ar', 'ranlib', 'work-dir'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
helper = Path(__file__).with_name('prepare-build-config.py')
base = [sys.executable, '-B', str(helper), '--host-perl', a.host_perl,
        '--target-config', a.target_config, '--sysroot', a.sysroot]
metadata = subprocess.check_output(base + ['--metadata-only'], text=True)
assert "prefix='/usr/pkg';" in metadata and 'installarchlib=' in metadata
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    out = Path(tmp) / 'config.json'
    subprocess.run(base + ['--cc', a.cc, '--ld', a.ld, '--ar', a.ar,
                          '--ranlib', a.ranlib, '--cflags=-O2',
                          '--ldflags=-pthread', '--output', str(out)], check=True)
    data = json.loads(out.read_text())
    assert data['cc'] == a.cc and data['ld'] == a.ld
    assert data['ccflags'] == '-O2' and data['optimize'] == ''
    assert data['osname'] == 'netbsd'
    assert data['archlibexp'].startswith(a.sysroot + '/')
    assert data['installvendorarch'].startswith('/usr/pkg/')
    bad = subprocess.run(base + ['--cc', 'cc', '--ld', a.ld, '--ar', a.ar,
                         '--ranlib', a.ranlib, '--output', str(out)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert bad.returncode != 0
    # Permit symlinks within the selected sysroot, never into the host.
    fixture = Path(tmp) / 'sysroot'
    cfg = fixture / 'perl'
    cfg.mkdir(parents=True)
    original = Path(a.target_config)
    shutil.copyfile(original, cfg / 'Config.real')
    shutil.copyfile(original.parent / 'Config_heavy.pl', cfg / 'heavy.real')
    (cfg / 'Config.pm').symlink_to('Config.real')
    (cfg / 'Config_heavy.pl').symlink_to('heavy.real')
    check = [sys.executable, '-B', str(helper), '--host-perl', a.host_perl,
             '--target-config', str(cfg / 'Config.pm'), '--sysroot', str(fixture),
             '--metadata-only']
    subprocess.run(check, check=True, stdout=subprocess.DEVNULL)
    (cfg / 'Config_heavy.pl').unlink()
    (cfg / 'Config_heavy.pl').symlink_to(original.parent / 'Config_heavy.pl')
    assert subprocess.run(check, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode != 0
    (cfg / 'Config.pm').unlink()
    (cfg / 'Config.pm').symlink_to(original)
    assert subprocess.run(check, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode != 0
print('Perl target build context: PASS')
