#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual pkgsrc queries; no LLVM compilation.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import fixture, load_sdk, module, write_json

sdk_source, args = load_sdk()
if len(args) != 4:
    sys.exit('Usage: llvm-reuse-adapter.py --sdk-source SDK PKGSRC MAKECONF BMAKE NEW_WORK')
pkgsrc, makeconf, bmake = map(os.path.realpath, args[:3])
work = Path(args[3])
if not work.is_absolute() or work.exists():
    sys.exit('new absolute work required')
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
common = work / 'common'
source = common / 'llvm-project-23.1.4.src/llvm'
build = source / 'cmake-pkgsrc-build'
build.mkdir(parents=True)
(common / '.build_makevars.mk').write_text('_MAKEVARS_MK= defined\nCFLAGS+= -DSTALE_CACHE=1\n')
env = dict(os.environ, MAKECONF=makeconf, PYTHONDONTWRITEBYTECODE='1', EMBERBSD_SDK_SOURCE=sdk_source)


def invoke(arguments, label=None):
    result = subprocess.run(arguments, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if label:
        (work / (label + '.log')).write_text(result.stdout)
    return result


fields = ['TOOLDIR', 'MACHINE_GNU_PLATFORM', 'MACHINE_ARCH', 'OPSYS', 'OS_VERSION', 'CMAKE']
command = [bmake, '-C', str(tree / 'lang/llvm'), '_PKGSRC_BARRIER=yes', '_MAKEVARS_MK=defined', 'WRKDIR=' + str(common)]
for key in fields:
    command.extend(['-v', key])
result = invoke(command)
assert result.returncode == 0, result.stdout
row = dict(zip(fields, result.stdout.splitlines()))
value = fixture(work, sdk_source, row['CMAKE'], source, build, tree / 'lang/llvm', tree / 'lang/llvm-devel', wrapper=False, include_empty=False)
value['runtime_work'] = str(common)
value['flags'] = {'obsolete': 'must not be copied'}
value['files']['compiler'] = [row['TOOLDIR'] + '/bin/' + row['MACHINE_GNU_PLATFORM'] + '-' + name for name in ('gcc', 'g++', 'strip')]
value['files']['patches'] = [str(path) for path in (tree / 'lang/llvm/patches').glob('patch-*')]
template = work / 'template.json'
write_json(template, value)
checks = []
reuse = module('reuse-package-stage')


def collect(role, label, *overrides):
    outer = work / label
    outer.mkdir(exist_ok=True)
    command = [bmake, '-C', str(tree / 'lang' / role), '_PKGSRC_BARRIER=yes', 'WRKDIR=' + str(outer),
        'EMBERBSD_LLVM_REUSE_INPUTS=' + str(template), 'EMBERBSD_LLVM_REUSE_PYTHON=' + sys.executable,
        'EMBERBSD_SDK_SOURCE=' + sdk_source, *overrides, 'llvm-reuse-inputs']
    result = invoke(command, label)
    if result.returncode:
        raise AssertionError(label + ': ' + result.stdout)
    return json.loads((outer / '.llvm-reuse-inputs.json').read_text())


runtime = collect('llvm', 'runtime')
sdk = collect('llvm-devel', 'sdk')
if runtime != sdk:
    delta = {k: (runtime['flags'].get(k), sdk['flags'].get(k)) for k in runtime['flags'] if runtime['flags'].get(k) != sdk['flags'].get(k)}
    raise AssertionError(f'current role inputs differ: {delta}')
assert 'obsolete' not in sdk['flags'] and 'STALE_CACHE' not in sdk['flags']['CFLAGS']
checks.extend(['current runtime/SDK inputs match at common root', 'template flags replaced', 'stale phase cache ignored'])
query_receipt = work / 'query-receipt.json'
write_json(query_receipt, dict(schema=2, context=runtime, inputs=reuse.snapshot(runtime), stage={}))
query_hash = hashlib.sha256(query_receipt.read_bytes()).hexdigest()
overrides = dict(CFLAGS='-DUSER_PATH="' + str(work / 'sdk') + '"', CONFIGURE_ENV='USER_VALUE=' + str(work / 'sdk'),
    MAKE_ENV='CPATH=/alternate/headers', CMAKE_BUILD_ARGS='-j 1 CXX_FLAGS=-DNEW_BUILD_CONTRACT',
    _CMAKE_BUILD_TOOL='/usr/bin/true', BUILD_TARGET='different-target', BUILD_DIRS='different-directory',
    CONFIGURE_DIR='different-configuration', SETENV='/usr/bin/env CPATH=/alternate/headers', RUN='export CPATH=/alternate/headers;')
for index, (key, setting) in enumerate(overrides.items()):
    label = 'override-' + str(index)
    changed = collect('llvm-devel', label, key + '=' + setting)
    assert changed != runtime, 'build override was ignored: ' + key
    assert setting in changed['flags'][key], 'literal input was rewritten: ' + key
    try:
        reuse.verify(str(work / label / '.llvm-reuse-inputs.json'), str(query_receipt), query_hash)
    except Exception as error:
        assert 'contract differs' in str(error), str(error)
    else:
        raise AssertionError('changed current input accepted: ' + key)
    checks.append('refuses current override: ' + key)
try:
    collect('llvm-devel', 'native-tool', 'EMBERBSD_BUILD_CMAKE=/usr/bin/true')
except AssertionError:
    checks.append('invalid current native tool refused')
else:
    raise AssertionError('invalid native tool accepted')
receipt = work / 'receipt.fixture'
receipt.write_text('not an accepted receipt')
base = [bmake, '-C', str(tree / 'lang/llvm-devel'), '_PKGSRC_BARRIER=yes', 'WRKDIR=' + str(work / 'reuse-sdk'),
    'EMBERBSD_LLVM_REUSE_INPUTS=' + str(template), 'EMBERBSD_LLVM_REUSE_PYTHON=' + sys.executable,
    'EMBERBSD_SDK_SOURCE=' + sdk_source, 'EMBERBSD_LLVM_REUSE_RECEIPT=' + str(receipt), 'EMBERBSD_LLVM_REUSE_SHA256=' + '0' * 64]
result = invoke(base + ['-v', 'NO_BUILD', '-v', 'NO_CONFIGURE', '-v', 'WRKSRC', '-v', 'PKG_FAIL_REASON'])
assert result.returncode == 0 and result.stdout.splitlines() == ['yes', 'yes', str(work / 'reuse-sdk/llvm-reuse'), ''], result.stdout
checks.append('opt-in private source disables second compilation')
(work / 'reuse-sdk').mkdir()
before = reuse.tree(str(common))
for target in ('do-extract', 'do-patch', 'do-install'):
    result = invoke(base + [target], target + '-refused')
    assert result.returncode and 'Accepted receipt drift' in result.stdout, result.stdout
    assert reuse.tree(str(common)) == before
    assert not (work / 'reuse-sdk/.destdir').exists() or not reuse.tree(str(work / 'reuse-sdk/.destdir'))
    checks.append(target + ' refuses unaccepted receipt before writes')
result = invoke(base + ['-C', str(tree / 'lang/llvm'), '-v', 'PKG_FAIL_REASON'])
assert result.returncode == 0 and 'requires the separate NetBSD cross SDK' in result.stdout
checks.append('runtime rejects SDK reuse')
reference = work / 'reference'
reference.mkdir()
accepted = work / 'accepted.json'
reuse.record(str(work / 'runtime/.llvm-reuse-inputs.json'), str(reference), str(accepted))
accepted_hash = hashlib.sha256(accepted.read_bytes()).hexdigest()
accepted_args = [arg for arg in base if not arg.startswith(('EMBERBSD_LLVM_REUSE_RECEIPT=', 'EMBERBSD_LLVM_REUSE_SHA256='))]
accepted_args += ['EMBERBSD_LLVM_REUSE_RECEIPT=' + str(accepted), 'EMBERBSD_LLVM_REUSE_SHA256=' + accepted_hash]
before = reuse.snapshot(runtime)
for target in ('do-extract', 'do-patch', 'do-install'):
    result = invoke(accepted_args + [target], target + '-accepted')
    assert result.returncode == 0, result.stdout
    assert reuse.snapshot(runtime) == before
assert reuse.tree(str(work / 'reuse-sdk/.destdir/usr/pkg')) == json.loads(accepted.read_text())['stage']
checks.append('actual make hooks install exact stage without object writes')
result = invoke(accepted_args + ['llvm-select-stage'], 'ordinary-selector')
assert result.returncode and 'missing complete-stage file:' in result.stdout, result.stdout
checks.append('ordinary PLIST check rejects incomplete LLVM fixture')
for kind in ('same-path', 'hardlink'):
    outer = work / ('receipt-collision-' + kind)
    outer.mkdir()
    output = outer / '.llvm-reuse-inputs.json'
    if kind == 'same-path':
        shutil.copyfile(accepted, output)
        protected = output
    else:
        os.link(accepted, output)
        protected = accepted
    before_hash = hashlib.sha256(protected.read_bytes()).hexdigest()
    arguments = [arg for arg in base if not arg.startswith(('WRKDIR=', 'EMBERBSD_LLVM_REUSE_RECEIPT=', 'EMBERBSD_LLVM_REUSE_SHA256='))]
    result = invoke(arguments + ['WRKDIR=' + str(outer), 'EMBERBSD_LLVM_REUSE_RECEIPT=' + str(protected), 'EMBERBSD_LLVM_REUSE_SHA256=' + before_hash, 'llvm-reuse-inputs'], 'collision-' + kind)
    assert hashlib.sha256(protected.read_bytes()).hexdigest() == before_hash, 'accepted receipt overwritten: ' + kind
    assert result.returncode and 'Context output replaces an input' in result.stdout, result.stdout
    checks.append('receipt SHA survives output collision: ' + kind)
write_json(work / 'results.json', dict(checks=checks, scope='Actual pkgsrc metadata/hooks with CMake fixture; no LLVM package acceptance.'))
print(f'PASS: {len(checks)} LLVM pkgsrc reuse adapter contracts')
