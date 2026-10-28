#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise ASLTS tool setup failure propagation without rebuilding tools."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--script', required=True, help='patched tests/aslts.sh')
parser.add_argument('--bash', required=True, help='selected host Bash')
args = parser.parse_args()
if not os.path.isabs(args.bash) or not os.access(args.bash, os.X_OK):
    parser.error('select an executable host Bash by absolute path')
source = Path(args.script).read_text()
start = source.index('build_acpi_tools()')
end = source.index('\n\n# Run a simple compiler test', start)
function = source[start:end]
with tempfile.TemporaryDirectory(prefix='acpi build tools test ', dir=os.environ.get('TMPDIR')) as temporary:
    root = Path(temporary)
    (root / 'bin').mkdir()
    (root / 'tmp').mkdir()
    for name in ('iasl', 'acpiexec', 'acpibin'):
        (root / 'bin' / name).write_text('fixture')
    setup = '\n'.join((f'generation_dir="{root}"',
        *(f'tmp_{name}="{root}/tmp/{name}"' for name in ('iasl', 'acpiexec', 'acpibin'))))
    cases = (('success', None, 'REBUILD_TOOLS=no'),
             ('make failure', None, 'REBUILD_TOOLS=yes\nmake() { return 42; }'),
             ('copy failure', None, 'REBUILD_TOOLS=no\ncp() { return 42; }'),
             ('missing tool', 'acpibin', 'REBUILD_TOOLS=no\nmake() { return 42; }'))
    for label, missing, control in cases:
        if missing:
            (root / 'bin' / missing).unlink()
        result = subprocess.run([args.bash, '-c', function + '\n' + setup + '\n' + control + '\nbuild_acpi_tools\n'],
                                cwd=root, text=True, capture_output=True, timeout=30)
        if (result.returncode == 0) != (label == 'success'):
            raise SystemExit(f'{label}: unexpected exit {result.returncode}\n{result.stdout}{result.stderr}')
        print(f'PASS: {label}')
