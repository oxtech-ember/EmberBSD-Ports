#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify equivalent pkgsrc patch paths and reject ambiguous metadata."""
import importlib.util, tempfile
from pathlib import Path
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p); e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
with tempfile.TemporaryDirectory() as td:
 r=Path(td); recipe=r/'recipe'; (recipe/'patches').mkdir(parents=True); (recipe/'distinfo').write_text('dist'); (recipe/'patches/patch-src').write_text('patch')
 expected=e.recipe_source_metadata(recipe); pkg=r/'pkg';pkg.mkdir(); key='fonts/harfbuzz/patches/patch-src'; digest=expected['patches']['patch-src']; dist=expected['distinfo']
 def check(lines):
  (pkg/'+BUILD_VERSION').write_text('\n'.join(lines)+'\n')
  e.validate_package_source(pkg, expected, recipe, distinfo=True, package_path='fonts/harfbuzz')
 check([f'fonts/harfbuzz/../../fonts/harfbuzz/patches/patch-src: {digest}',f'fonts/harfbuzz/distinfo: {dist}'])
 for lines in ([f'{key}: {digest}',f'fonts/harfbuzz/../../fonts/harfbuzz/patches/patch-src: {digest}',f'fonts/harfbuzz/distinfo: {dist}'], [f'../../{key}: {digest}',f'fonts/harfbuzz/distinfo: {dist}']):
  try: check(lines)
  except ValueError: pass
  else: raise AssertionError('ambiguous or escaping metadata accepted')
print('PASS: canonical relative patch paths and rejection of collisions/escape')
