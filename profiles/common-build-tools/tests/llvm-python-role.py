#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual post-barrier Python build roles.
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk_source, args = load_sdk()
if len(args) != 4:
    sys.exit('Use PKGSRC MAKECONF BMAKE NEW_WORK')
pkgsrc, makeconf, bmake = map(os.path.realpath, args[:3])
work = Path(args[3]).absolute()
(work / 'pkgsrc/lang').mkdir(parents=True)
tree = work / 'pkgsrc'
profile = Path(__file__).resolve().parents[1]
for name in os.listdir(pkgsrc):
    if not name.startswith('.') and name != 'lang':
        (tree / name).symlink_to(Path(pkgsrc) / name)
for name in os.listdir(pkgsrc + '/lang'):
    if name not in ('llvm', 'llvm-devel'):
        (tree / 'lang' / name).symlink_to(Path(pkgsrc) / 'lang' / name)
for name in ('llvm', 'llvm-devel'):
    shutil.copytree(profile / '../../pkgsrc/lang' / name, tree / 'lang' / name)
variables = 'PKGNAME WRKDIR CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CMAKE_CONFIGURE_ARGS CONFIGURE_ENV PYTHON_FOR_BUILD_ONLY PYTHONBIN REPLACE_PYTHON DEPENDS BUILD_DEPENDS TOOL_DEPENDS BUILDLINK_DEPMETHOD.py-llvm-lit'.split()
rows = []
for package, cross in [('llvm', 'yes'), ('llvm-devel', 'yes'), ('llvm', 'no')]:
    command = [bmake, '-C', str(tree / 'lang' / package), '_PKGSRC_BARRIER=yes', '_MAKEVARS_MK=defined', 'USE_CROSS_COMPILE=' + cross, 'WRKDIR=' + str(work / 'common')]
    for key in variables:
        command.extend(['-v', key])
    result = subprocess.run(command, env=dict(os.environ, MAKECONF=makeconf, EMBERBSD_SDK_SOURCE=sdk_source), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    rows.append(dict(zip(variables, result.stdout.splitlines())))
(work / 'query.json').write_text(json.dumps(rows, indent=2) + '\n')
runtime, sdk, native = rows
for field in ('CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CMAKE_CONFIGURE_ARGS', 'CONFIGURE_ENV'):
    assert runtime[field] == sdk[field], 'Cross inputs differ: ' + field
assert [r['PKGNAME'] for r in rows] == ['llvm-23.1.3nb1', 'llvm-devel-23.1.3nb2', 'llvm-23.1.3']
assert all(r['PYTHON_FOR_BUILD_ONLY'] == 'tool' and re.search(r'python[0-9]+>=', r['TOOL_DEPENDS']) and r['BUILDLINK_DEPMETHOD.py-llvm-lit'] == 'build' for r in (runtime, sdk))
assert not re.search(r'python[0-9]+|llvm-lit', runtime['DEPENDS'])
assert re.search(r'python[0-9]+>=', sdk['DEPENDS']) and 'llvm-lit-23.1.3' in sdk['DEPENDS']
assert runtime['PYTHONBIN'] == sdk['PYTHONBIN'] and sdk['PYTHONBIN'].startswith('/usr/pkg/bin/python') and runtime['REPLACE_PYTHON'] == sdk['REPLACE_PYTHON']
assert native['PYTHON_FOR_BUILD_ONLY'] == 'no' and re.search(r'/include/python[0-9.]+', native['CFLAGS']) and 'llvm-lit-23.1.3' in native['DEPENDS']
print('PASS: exact common-root post-barrier compile inputs, Python/lit roles, native behavior and target shebangs; metadata only')
