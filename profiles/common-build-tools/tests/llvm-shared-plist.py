#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Shared LLVM install must materialize the selected PLIST.
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

BMAKE = os.environ.get('BMAKE') or sys.exit('BMAKE must name selected BSD make')
TMPDIR = os.environ.get('TMPDIR') or sys.exit('TMPDIR must name a C-local scratch directory')
root = Path(__file__).resolve().parents[1]
makefile = root / '../../pkgsrc/lang/llvm/Makefile'
reuse = root / '../../pkgsrc/lang/llvm/reuse.mk'
text = makefile.read_text()
framework = text.index('.include "../../mk/bsd.pkg.mk"')
dependencies = list(re.finditer(r'^llvm-shared-install: \$\{PLIST\}$', text, re.M))
assert len(dependencies) <= 1, 'Makefile must add at most one selected PLIST dependency'
dependency = dependencies[0] if dependencies else None
if dependency is not None:
    assert dependency.start() > framework, 'shared install PLIST dependency must follow bsd.pkg.mk'
assert 'llvm-shared-install: ${PLIST}' not in reuse.read_text(), 'PLIST is undefined when reuse.mk is parsed'

with tempfile.TemporaryDirectory(prefix='llvm-shared-plist-', dir=TMPDIR) as directory:
    work = Path(directory)
    (work / 'source').mkdir()
    (work / 'files').mkdir()
    (work / 'stage').mkdir()
    for name, entry in (
        ('full', 'full-entry'),
        ('runtime', 'runtime-entry'),
        ('devel', 'devel-entry'),
        ('selected', 'devel-entry'),
    ):
        (work / name).write_text(entry + '\n')
    selector = work / 'files/select-package-stage.py'
    selector.write_text('''from pathlib import Path
import sys
selected = Path(sys.argv[-1])
if not selected.is_file():
    raise SystemExit(f"missing selected PLIST: {selected}")
if selected.read_text() != "devel-entry\\n":
    raise SystemExit("selected PLIST does not match the devel partition")
''')
    recipe = work / 'Makefile'
    recipe_text = f'''_EMBERBSD_LLVM_SHARED_DEVEL= yes
WRKDIR= {work}
EMBERBSD_LLVM_SHARED_STAGE= {work}/stage
DESTDIR= {work}/dest
PREFIX= /usr/pkg
TOOL_PYTHONBIN= {sys.executable}
FILESDIR= {work}/files
EMBERBSD_SDK_SOURCE= {work}
LLVM_FULL_PLIST_SRC= {work}/full
LLVM_RUNTIME_PLIST_SRC= {work}/runtime
LLVM_DEVEL_PLIST_SRC= {work}/devel
.include "{reuse}"

# Model pkgsrc's later PLIST definition from mk/plist/plist.mk.
PLIST= {work}/.PLIST
PLIST_SRC= {work}/selected
${{PLIST}}: ${{PLIST_SRC}}
\t${{TOOL_PYTHONBIN}} -c "import shutil; shutil.copyfile('${{.ALLSRC}}', '${{.TARGET}}')"

'''
    # Use the real production dependency, at its actual late parse position.
    recipe.write_text(recipe_text + (dependency.group(0) + '\n' if dependency else ''))
    result = subprocess.run(
        [BMAKE, '-C', str(work), '-f', str(recipe), 'do-install'],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if dependency is None:
        assert result.returncode != 0 and 'missing selected PLIST:' in result.stdout, result.stdout
        raise SystemExit('Makefile is missing late PLIST dependency; bmake reached the selector failure')
    if result.returncode:
        raise SystemExit(result.stdout)
    selected = work / '.PLIST'
    assert selected.is_file() and selected.read_text() == 'devel-entry\n'
print('PASS: shared install generates the selected PLIST after alternate lists')
