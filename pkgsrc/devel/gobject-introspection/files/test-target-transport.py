#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check selected SSH transport arguments without contacting a target."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk-source', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.sdk_source / 'src'))
sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location('target_query', Path(__file__).with_name('target-query.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(dir=a.work_dir) as temporary:
    root = Path(temporary)
    ssh = root / 'ssh'
    ssh.write_text('#!' + sys.executable + '\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
    ssh.chmod(0o700)
    conf = root / 'config'
    conf.write_text('mock config\n')
    base = {'ssh': 'root@host.example'}
    legacy = module.ssh_command(base)
    assert legacy[0] == 'ssh' and legacy[-1] == base['ssh']
    selected = module.ssh_command(dict(base, ssh_executable=str(ssh), ssh_config=str(conf), ssh_port=2222))
    assert selected[0] == str(ssh)
    assert selected[selected.index('-F') + 1] == str(conf)
    assert selected[selected.index('-p') + 1] == '2222'
    assert '-o' in selected and 'StrictHostKeyChecking=yes' in selected and selected[-1] == base['ssh']
    observed = subprocess.run([*selected, 'ordinary probe'], capture_output=True, text=True, check=True)
    assert json.loads(observed.stdout) == [*selected[1:], 'ordinary probe']
    for updates in ({'ssh_executable': 'ssh'}, {'ssh_config': 'relative'}, {'ssh_port': 0},
                    {'ssh_port': True}, {'ssh_port': 65536}, {'ssh': 'host;command'}):
        try:
            module.ssh_command(dict(base, **updates))
        except (module.QueryError, OSError, ValueError):
            pass
        else:
            raise AssertionError('invalid transport accepted: ' + repr(updates))
print('selected SSH transport: PASS')
