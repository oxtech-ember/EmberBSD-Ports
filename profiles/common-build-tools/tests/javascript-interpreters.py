#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check common JS executable and source-only package contracts."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

if len(sys.argv) != 3:
    sys.exit('Usage: javascript-interpreters.py BMAKE EXPORTED_PKGSRC')
make, tree = sys.argv[1], Path(sys.argv[2])
helper = Path(__file__).resolve().parents[1] / 'javascript.mk'
with tempfile.TemporaryDirectory(prefix='js-interpreter-') as temp:
    root = Path(temp)
    for name in ('mk', 'devel/fixture', 'lang/nodejs', 'lang/python'):
        (root / name).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(helper, root / 'mk/emberbsd-javascript.mk')
    shutil.copyfile(tree / 'lang/nodejs/application.mk', root / 'lang/nodejs/application.mk')
    (root / 'lang/python/tool.mk').write_text('')
    fixture = root / 'devel/fixture/Makefile'
    for name, executable in [('semver', 'bin/semver.js'), ('asar', 'bin/asar.mjs'),
                             ('which', 'bin/which.js'), ('library', '')]:
        fixture.write_text('PREFIX= /selected-prefix\nDO_NADA= :\n' +
                           (f'REPLACE_NODEJS= {executable}\n' if executable else '') +
                           '.include "../../mk/emberbsd-javascript.mk"\n')
        query = subprocess.run([make, '-C', str(fixture.parent), '-v', 'NO_CONFIGURE',
                                '-v', 'DEPENDS', '-v', 'REPLACE_FILES.nodejs',
                                '-v', 'REPLACE.nodejs.new'], capture_output=True, text=True, check=True)
        no_configure, depends, replace, interpreter = query.stdout.splitlines()
        if executable:
            assert not no_configure and 'nodejs>=26:../../lang/nodejs' in depends, name
            assert replace == executable and interpreter == '/selected-prefix/bin/node', name
            run = subprocess.run([make, '-C', str(fixture.parent), '-n', 'do-configure'],
                                 capture_output=True, text=True, check=True)
            assert ':' in run.stdout, name
        else:
            assert no_configure == 'yes' and not depends and not replace and not interpreter, name
print('PASS: JS CLI interpreter/dependency selection and source-only behavior')
