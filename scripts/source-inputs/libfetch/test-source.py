#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check a prepared libfetch payload and rejection of accidental changes."""
import shutil
import importlib.util
import types
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
        subprocess.run(base + ['verify-source', '--source', command[-1], '--patch', patch,
                               '--pkgsrc-export', str(shared)],
                       check=True, stdout=subprocess.DEVNULL)
        # A v2 selection must never invoke the expensive canonical exporter.
        sys.path.insert(0, str(ports / 'pkgsrc/lang/llvm/files'))
        import sdk_source
        sdk_source.load_sdk(['--sdk-source', sdk])
        from emberbsd_sdk.errors import SDKError
        spec = importlib.util.spec_from_file_location('libfetch_owner_test', script)
        owner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(owner)
        owner.SDK_SOURCE = Path(sdk)
        owner.SDKError = SDKError
        def forbidden_export(*args, **kwargs):
            raise AssertionError('v2 invoked the canonical exporter')
        owner.process = types.SimpleNamespace(capture=forbidden_export)
        owner.export_tree(Path(temp), git, patch, str(shared))
        # A matching legacy v1 key selects the export without a canonical export.
        receipt_path = shared / 'pkgsrc-export.json'
        v2 = receipt_path.read_text()
        legacy = json.loads(v2)
        legacy['version'] = 1
        del legacy['material']
        receipt_path.write_text(json.dumps(legacy))
        owner.export_tree(Path(temp), git, patch, str(shared))
        subprocess.run(command[:-1] + [str(Path(temp) / 'from-v1')],
                       check=True, stdout=subprocess.DEVNULL)
        receipt_path.write_text(v2)
        # A matching key reuses the prepared source without rereading FILESDIR.
        target = shared / 'pkgsrc/net/libfetch/files/common.c'
        original = target.read_bytes()
        target.write_bytes(original + b'\n/* not read again */\n')
        result = subprocess.run(base + ['verify-source', '--source', command[-1],
                                        '--patch', patch, '--pkgsrc-export', str(shared)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        target.write_bytes(original)
        if result.returncode != 0:
            raise SystemExit('matching key reread the shared FILESDIR: ' + result.stderr.decode())
print('libfetch source verification PASS')
