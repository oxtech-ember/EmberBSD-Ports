#!/usr/bin/env python3
"""Check cwrappers selection with the actual native and cross pkgsrc paths."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('bmake', 'pkgsrc', 'baseline-pkgsrc', 'stage-makeconf', 'native-makeconf', 'cross-makeconf', 'stage-cwrappers', 'stage-root', 'rpcgen'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
def query(source, makeconf, *args, cross=False):
    return subprocess.check_output([str(a.bmake), '-C', str(source/'lang/clang'),
        'MAKECONF='+str(makeconf), *([] if cross else ['EMBERBSD_DARWIN_BOOTSTRAP=yes']),
        '_PKGSRC_BARRIER=yes', *args, '-V', '${CWRAPPERS_SRC_DIR}', '-V', '${TOOLS_PATH.rpcgen}'], text=True).splitlines()
selected = query(a.pkgsrc, a.stage_makeconf)
assert selected == [str(a.stage_cwrappers), str(a.rpcgen)], selected
# Verify only the wrapper roles used by this Clang build, not the full set.
assert a.stage_cwrappers.resolve().is_relative_to(a.stage_root.resolve())
for role in ('cc-wrapper', 'c++-wrapper', 'ld-wrapper'):
    tool = a.stage_cwrappers/role
    assert tool.is_file() and os.access(tool, os.X_OK) and tool.resolve().is_relative_to(a.stage_root.resolve()), tool
assert query(a.pkgsrc, a.native_makeconf)[0] == query(a.baseline_pkgsrc, a.native_makeconf)[0]
assert query(a.pkgsrc, a.cross_makeconf, cross=True)[0] == query(a.baseline_pkgsrc, a.cross_makeconf, cross=True)[0]
with tempfile.TemporaryDirectory(prefix='stage-tool-override-') as root:
    root = Path(root).resolve(); explicit = root/'explicit-wrappers'
    config = root/'make.conf'
    config.write_text('.include "'+str(a.stage_makeconf)+'"\nCWRAPPERS_SRC_DIR= '+str(explicit)+'\n')
    assert query(a.pkgsrc, config)[0] == str(explicit)
    command = root/'command-wrappers'
    assert query(a.pkgsrc, config, 'CWRAPPERS_SRC_DIR='+str(command))[0] == str(command)
print('PASS: staged rpcgen and cwrappers, default, cross and explicit overrides')
