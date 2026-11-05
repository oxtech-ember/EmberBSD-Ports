#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the actual common JS install target and backup path checks."""
from pathlib import Path
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    sys.exit('Usage: javascript-patch-backups.py BMAKE')
helper = Path(__file__).resolve().parents[1] / 'javascript.mk'
with tempfile.TemporaryDirectory(prefix='js-backups-') as temp:
    root = Path(temp)
    for name in ('mk', 'devel/fixture', 'lang/python', 'src/bin', 'dest'):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / 'mk/emberbsd-javascript.mk').write_bytes(helper.read_bytes())
    (root / 'lang/python/tool.mk').write_text('')
    (root / 'src/bin/generated.orig').write_text('generated')
    (root / 'src/upstream.orig').write_text('upstream')
    fixture = root / 'devel/fixture/Makefile'
    fixture.write_text(f'''PREFIX= /usr/pkg
DESTDIR= {root}/dest
WRKSRC= {root}/src
JS_MODULE_NAME= fixture
JS_MODULE_PATCH_BACKUPS?= bin/generated.orig
INSTALL_DATA_DIR= /bin/mkdir -p
CP= /bin/cp
RM= /bin/rm -f
ECHO= /bin/echo
.include "../../mk/emberbsd-javascript.mk"
''')
    def run(backup):
        return subprocess.run([sys.argv[1], '-C', str(fixture.parent),
                               'JS_MODULE_PATCH_BACKUPS=' + backup, 'do-install'],
                              capture_output=True, text=True)
    assert run('bin/generated.orig').returncode == 0
    dst = root / 'dest/usr/pkg/lib/node_modules/fixture'
    assert not (dst / 'bin/generated.orig').exists()
    assert (dst / 'upstream.orig').read_text() == 'upstream'
    assert (root / 'src/bin/generated.orig').read_text() == 'generated'
    for invalid in ('/absolute.orig', '../outside.orig', 'bin/../outside.orig', 'bin/generated'):
        assert run(invalid).returncode != 0, invalid
print('PASS: selected patch backups removed; upstream files and path boundary preserved')
