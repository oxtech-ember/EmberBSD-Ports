#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Complete exported recipe with actual BSD make.
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 6:
    sys.exit('Use EXPORTED_PKGSRC RECIPE_MAKEFILE BMAKE HOST_MAKECONF CROSS_MAKECONF NEW_OUTPUT')
tree, recipe, make, host, cross = map(os.path.realpath, args[:5])
out = Path(args[5]).absolute()
out.mkdir()
queries = 'PKGNAME _PYTHON_VERSION PYTHONBIN PKG_FAIL_REASON OPSYS MACHINE_ARCH USE_CROSS_COMPILE'.split()
results = []


def run(name, config, extra=(), reject=False):
    argv = [make, '-C', tree + '/devel/py-llvm-lit', '-f', recipe, 'MAKECONF=' + config, 'WRKOBJDIR=' + str(out / 'objects'), *extra]
    for key in queries:
        argv.extend(['-v', key])
    result = subprocess.run(argv, capture_output=True, text=True)
    (out / (name + '.log')).write_text(result.stdout + result.stderr)
    values = result.stdout.splitlines()
    assert result.returncode == 0 and len(values) == len(queries), result.stderr
    data = dict(zip(queries, values))
    results.append(dict(case=name, argv=argv, values=data, exit=result.returncode))
    (out / 'receipt.json').write_text(json.dumps(results, indent=2) + '\n')
    if reject:
        assert data['PKG_FAIL_REASON'], 'unsupported Python accepted'
    else:
        assert data['PKGNAME'] == 'py315-llvm-lit-23.1.4nb1' and data['_PYTHON_VERSION'] == '315' and data['PYTHONBIN'].endswith('/bin/python3.15') and not data['PKG_FAIL_REASON'], str(data)
    return data


native, target, recursive = run('native', host), run('cross', cross), run('native-recursive', cross, ['USE_CROSS_COMPILE=no'])
assert target['OPSYS'] == 'NetBSD' and target['MACHINE_ARCH'] in ('x86_64', 'aarch64')
assert recursive['OPSYS'] == native['OPSYS'] and recursive['MACHINE_ARCH'] == native['MACHINE_ARCH'] and recursive['USE_CROSS_COMPILE'] == 'no'
for name, config in [('native', host), ('cross', cross)]:
    for version in ('314', '316'):
        run(name + '-reject-' + version, config, ['PYTHON_VERSION_REQD=' + version], True)
print('PASS: native, cross and recursive-host lit select Python315; unsupported requests fail')
