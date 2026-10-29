#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise an installed AutoGen tearoff with selected tools and pkgsrc export."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from recipe import generation_recipe

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'export', 'host-prefix', 'pkg-admin', 'make', 'makeconf', 'git', 'patch', 'work-dir'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--make-arg', action='append', default=[])
a = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', a.sdk_source]
for key in ('export', 'host-prefix', 'pkg-admin', 'make', 'makeconf', 'git', 'patch'):
    base.extend(['--' + key, getattr(a, key.replace('-', '_'))])
for value in a.make_arg:
    base.extend(['--make-arg', value])

def run(*extra, ok=True):
    result = subprocess.run([*base, *map(str, extra)], capture_output=True, text=True)
    if (result.returncode == 0) != ok:
        raise AssertionError(result.stderr or result.stdout)
    return result

with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    recipe = Path(tmp) / 'recipe'
    shutil.copytree(Path(a.export) / 'pkgsrc/devel/autogen', recipe)
    signature = generation_recipe(recipe)
    with (recipe / 'Makefile').open('a') as out:
        out.write('\n# documentation\nCOMMENT=metadata only\n')
    assert generation_recipe(recipe) == signature
    with (recipe / 'Makefile').open('a') as out:
        out.write('CONFIGURE_ARGS+=--changed-generation\n')
    assert generation_recipe(recipe) != signature
    source = Path(tmp) / 'source'
    run('--output', source)
    run('--source', source)
    verify = [sys.executable, '-B', str(owner), '--sdk-source', a.sdk_source, '--git', a.git,
              'verify-source', '--source', str(source), '--patch', a.patch, '--pkgsrc-export', a.export]
    subprocess.run(verify, check=True, capture_output=True)
    # Exercise the owner verifier against an export containing only the
    # relevant recipe, with unchanged metadata versus changed generation.
    fixture = Path(tmp) / 'export'
    (fixture / 'pkgsrc/devel').mkdir(parents=True)
    shutil.copy2(Path(a.export) / 'pkgsrc-export.json', fixture / 'pkgsrc-export.json')
    shutil.copy2(Path(a.export) / 'pkgsrc/EMBERBSD-PKGSRC-REVISION', fixture / 'pkgsrc/EMBERBSD-PKGSRC-REVISION')
    shutil.copytree(Path(a.export) / 'pkgsrc/devel/autogen', fixture / 'pkgsrc/devel/autogen')
    modified = fixture / 'pkgsrc/devel/autogen/Makefile'
    with modified.open('a') as out:
        out.write('\n# metadata only\nCOMMENT=description only\n')
    modified_verify = [*verify[:-1], str(fixture)]
    subprocess.run(modified_verify, check=True, capture_output=True)
    with modified.open('a') as out:
        out.write('CONFIGURE_ARGS+=--changed-generation\n')
    assert subprocess.run(modified_verify, capture_output=True).returncode != 0
    run('--output', source, ok=False)
    (source / 'unexpected').write_text('changed\n')
    run('--source', source, ok=False)
    assert subprocess.run(verify, capture_output=True).returncode != 0
    (source / 'unexpected').unlink()
    run('--source', source)
    run('--make-arg', 'CONFIGURE_ARGS=--changed', '--source', source, ok=False)
print('AutoGen libopts common source: PASS')
