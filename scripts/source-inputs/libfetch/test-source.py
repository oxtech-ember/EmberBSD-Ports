#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check a prepared libfetch payload and rejection of accidental changes."""
import shutil
import json
import subprocess
import sys
import tempfile
from pathlib import Path

if len(sys.argv) not in (5, 6):
    raise SystemExit('usage: test-source.py PYTHON SDK_SOURCE GIT PREPARED_SOURCE [PATCH]')
python, sdk, git, source = sys.argv[1:5]
source = Path(source).resolve(strict=True)
script = Path(__file__).with_name('source.py')
base = [python, '-B', str(script), '--sdk-source', sdk, '--git', git]
with tempfile.TemporaryDirectory(prefix='libfetch-test-') as temp:
    copy = Path(temp) / 'source'
    shutil.copytree(source, copy)
    def verify():
        return subprocess.run(base + ['verify-source', '--source', str(copy)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE).returncode
    if verify() != 0:
        raise SystemExit('valid source did not verify')
    with (copy / 'common.c').open('ab') as handle:
        handle.write(b'\n/* test change */\n')
    if verify() == 0:
        raise SystemExit('changed source was accepted')
    shutil.copyfile(source / 'common.c', copy / 'common.c')
    receipt = copy / 'emberbsd-prepared-source.json'
    data = json.loads(receipt.read_text())
    data['package'] = 'wrong/package'
    receipt.write_text(json.dumps(data))
    if verify() == 0:
        raise SystemExit('wrong package identity was accepted')
    result = subprocess.run(base + ['prepare', '--patch', '/usr/bin/false', '--output', str(copy)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode == 0:
        raise SystemExit('existing source output was overwritten')
    if len(sys.argv) == 6:
        patch = sys.argv[5]
        shared = Path(temp) / 'shared'
        ports = script.resolve().parents[3]
        subprocess.run([python, '-B', str(ports / 'scripts/pkgsrc-shared-export.py'),
                        '--sdk-source', sdk, '--git', git, '--patch', patch, str(shared)],
                       check=True, stdout=subprocess.DEVNULL)
        command = base + ['prepare', '--patch', patch, '--pkgsrc-export', str(shared),
                          '--output', str(Path(temp) / 'from-shared')]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        with (shared / 'pkgsrc/net/libfetch/files/common.c').open('ab') as handle:
            handle.write(b'\n/* test change */\n')
        command[-1] = str(Path(temp) / 'changed-shared')
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode == 0 or b'differs from current export' not in result.stderr:
            raise SystemExit('changed shared export was not rejected')
print('libfetch source verification PASS')
