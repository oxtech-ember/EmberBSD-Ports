#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compare checkout and real pkgsrc-export source preparation and validation."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'pkgsrc', 'archive', 'patch', 'git', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
owner = Path(__file__).resolve().parents[1]
checkout = owner / 'files/runtime.py'
export = a.pkgsrc.resolve(strict=True)
exported = export / 'lang/compiler-rt/files/runtime.py'
work = a.work
if not work.is_absolute() or work.exists():
    parser.error('work must be an absolute new directory')
work.mkdir()


def run(argv, success=True):
    result = subprocess.run([str(x) for x in argv], capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(result.stderr)
    return result


common = [sys.executable, '-B', '-S']
v1 = [*common, checkout, '--sdk-source', a.sdk_source]
v2 = [*common, exported, '--sdk-source', a.sdk_source, '--pkgsrc-root', export]
source1, source2 = work / 'checkout-source', work / 'export-source'
args = ['--archive', a.archive, '--patch', a.patch]
a1 = json.loads(run([*v1, 'prepare', *args, '--source', source1, '--git', a.git]).stdout)
a2 = json.loads(run([*v2, 'prepare', *args, '--source', source2]).stdout)
assert (a1['version'], a2['version']) == (1, 2)
assert a2['recipe']['ports_revision'] is None
assert a1['recipe']['files'] == a2['recipe']['files']
assert a1['tree_sha256'] == a2['tree_sha256']
run([*v1, 'verify-source', '--source', source2, '--git', a.git])
run([*v2, 'verify-source', '--source', source1])

# Mutate only a disposable copy of exported recipes; checksum refusal must
# happen before an altered patch can be accepted as the common source.
copy = work / 'recipe-copy'
for package in ('compiler-rt', 'llvm'):
    shutil.copytree(export / 'lang' / package, copy / 'lang' / package)
patch = copy / 'lang/compiler-rt/patches/patch-00-binary128-fenv'
patch.write_bytes(patch.read_bytes() + b'\nchanged test byte\n')
copy_cli = [*common, copy / 'lang/compiler-rt/files/runtime.py', '--sdk-source', a.sdk_source,
            '--pkgsrc-root', copy]
result = run([*copy_cli, 'verify-source', '--source', source2], False)
assert 'patch checksum differs' in result.stderr
print('checkout/export identical source, cross-verification and changed patch refusal: PASS')
