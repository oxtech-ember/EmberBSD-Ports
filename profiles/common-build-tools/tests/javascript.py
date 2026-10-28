#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check common JavaScript source identity and dependency declarations."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).resolve().parents[1] / 'javascript-validate.py'
with tempfile.TemporaryDirectory(prefix='js module ') as temp:
    root = Path(temp)
    def write(deps=None):
        (root / 'package.json').write_text(json.dumps({'name': '@test/module', 'version': '1.2.3',
                                                       'dependencies': deps or {}}))
    def run(*extra):
        return subprocess.run([sys.executable, '-B', '-I', '-S', str(script), '--source', str(root),
                               '--name', '@test/module', '--version', '1.2.3', *extra],
                              text=True, capture_output=True)
    write(); assert run().returncode == 0
    write({'other': '^1'}); assert run().returncode != 0
    assert run('--dependency', 'other').returncode == 0
    assert run('--dependency', 'other', '--dependency', 'other').returncode != 0
    (root / 'node_modules').mkdir(); assert run('--dependency', 'other').returncode != 0
    (root / 'node_modules').rmdir()
    (root / 'Node_Modules').mkdir(); assert run('--dependency', 'other').returncode != 0
    (root / 'Node_Modules').rmdir()
    (root / 'NODE_MODULES').touch(); assert run('--dependency', 'other').returncode != 0
    (root / 'NODE_MODULES').unlink()
    (root / 'link').symlink_to(root / 'package.json'); assert run('--dependency', 'other').returncode != 0
print('common JS package identity, dependencies and no nested stack PASS')
