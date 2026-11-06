#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check active patch-target detection with the selected bmake."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--sdk-source', type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk import paths
spec = importlib.util.spec_from_file_location('refresh', Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='active-patch-test-') as tmp:
 root=Path(tmp).resolve(); recipe=root/'recipe'; recipe.mkdir(); framework=root/'patch.mk'
 for target in ('do-patch', 'do-extract'):
  m.active_parse_trace.cache_clear()
  framework.write_text('.if !target('+target+')\n'+target+': pkgsrc-action\n.endif\npkgsrc-action:\n\t@:\n')
  makefile=recipe/'Makefile'
  makefile.write_text('PKGNAME=fixture\n.if defined(CUSTOM)\n'+target+': custom-action\ncustom-action:\n\t@:\n.endif\n.include "'+str(framework)+'"\n')
  cmd=[str(a.bmake),'-C',str(recipe)]
  files=str(makefile)+' '+str(framework); allowed={framework.resolve()}
  m.validate_active_target(paths,cmd,recipe,files,allowed, target)
  try:m.validate_active_target(paths,cmd+['CUSTOM=yes'],recipe,files,allowed, target)
  except ValueError as e:assert 'active custom' in str(e)
  else:raise AssertionError('active custom target accepted')
  for index, trace in enumerate(('', 'Parsing malformed origin\nParseDependency('+target+': anything)\n', 'ParseDependency('+target+': anything)\n')):
   fake=root/('fake-bmake-'+target+'-'+str(index)); fake.write_text('#!'+sys.executable+'\nimport sys\nsys.stdout.write("fixture\\n");sys.stderr.write('+repr(trace)+')\n'); fake.chmod(0o755)
   try:m.validate_active_target(paths,[str(fake)],recipe,files,allowed, target)
   except ValueError as e:assert 'trace' in str(e)
   else:raise AssertionError('invalid trace accepted')
 # Both guards use the same cached parse for the same old/new invocation.
 framework.write_text('.if !target(do-patch)\ndo-patch: p\n.endif\n.if !target(do-extract)\ndo-extract: e\n.endif\np e:\n\t@:\n')
 makefile.write_text('PKGNAME=fixture\n.if 0\ndo-patch: custom\ndo-extract: custom\n.endif\n.include "'+str(framework)+'"\n')
 m.active_parse_trace.cache_clear()
 m.validate_active_target(paths,cmd,recipe,files,allowed,'do-patch')
 m.validate_active_target(paths,cmd,recipe,files,allowed,'do-extract')
 assert m.active_parse_trace.cache_info().misses==1 and m.active_parse_trace.cache_info().hits==1
print('PASS: selected bmake distinguishes inactive and active targets; malformed/absent trace refused')
