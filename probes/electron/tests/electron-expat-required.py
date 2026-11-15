#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the common Expat provider is unconditional in both owner CLIs."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]; owner=root/'pkgsrc/devel/electron44/files'
for file,phase in [('build-electron.py','configure'),('host-buildlink.py',None)]:
 cmd=[sys.executable,'-B',str(owner/file)] + ([phase] if phase else []) + ['--help']
 r=subprocess.run(cmd,text=True,capture_output=True); assert r.returncode==0,r.stderr
 assert '--shared-expat' not in r.stdout, 'removed optional provider must not be exposed'
producer=(root/'pkgsrc/devel/electron44/producer.mk').read_text()
assert 'EMBERBSD_ELECTRON_SHARED_EXPAT' not in producer
for n in ('host-dependencies.mk','runtime-dependencies.mk'):
 text=(root/'pkgsrc/devel/electron44'/n).read_text(); assert 'EMBERBSD_ELECTRON_SHARED_EXPAT' not in text
 assert 'expat>=2.10.0nb1' in text and '../../textproc/expat/buildlink3.mk' in text
print('PASS: common Expat has no optional switch and both dependency floors are explicit')
