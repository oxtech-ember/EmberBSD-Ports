#!/usr/bin/env python3
"""Check the native-stage rpcgen wrapper's executable boundary at use."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('bmake', 'pkgsrc', 'python'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
with tempfile.TemporaryDirectory(prefix='rpcgen-stage-guard-') as tmp:
    root = Path(tmp).resolve(); stage = root/'stage'; prefix = '/selected-host'
    tool = stage/'selected-host/bin/rpcgen'; tool.parent.mkdir(parents=True)
    def executable(path):
        path.write_text('#!'+str(a.python)+'\nprint("rpcgen fixture")\n')
        path.chmod(0o755)
    executable(tool)
    makefile = root/'Makefile'
    makefile.write_text('''OPSYS= Darwin
USE_CROSS_COMPILE= no
EMBERBSD_NATIVE_STAGE_ROOT= {stage}
EMBERBSD_NATIVE_STAGE_PREFIX= {prefix}
EMBERBSD_NATIVE_STAGE_PYTHON= {python}
TOOLS_PATH.rpcgen= {tool}
WRAPPER_BINDIR= {root}
TOOLS_SCRIPT_DFLT.rpcgen= ${{TOOLS_PATH.rpcgen:Q}} "$$@"
.include "{rpcgen_mk}"
all:
\t${{TOOLS_SCRIPT.rpcgen}}
'''.format(stage=stage, prefix=prefix, python=a.python, tool=tool,
           root=root, rpcgen_mk=a.pkgsrc/'mk/tools/rpcgen.mk'))
    def run(*args):
        return subprocess.run([str(a.bmake), '-r', '-f', str(makefile), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    good = run(); assert good.returncode == 0 and 'rpcgen fixture' in good.stdout, good.stdout
    tool.unlink()
    missing = run(); assert missing.returncode != 0 and 'rpcgen must resolve' in missing.stdout, missing.stdout
    outside = root/'outside'; executable(outside); tool.symlink_to(outside)
    escaped = run(); assert escaped.returncode != 0 and 'rpcgen must resolve' in escaped.stdout, escaped.stdout
    cross = run('OPSYS=NetBSD', 'USE_CROSS_COMPILE=yes')
    assert cross.returncode == 0 and 'rpcgen fixture' in cross.stdout, cross.stdout
print('PASS: native stage rpcgen, missing/escape refusal and cross unchanged')
