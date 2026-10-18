#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Typed process recovery policy, no producers.
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk, module, write_json
sdk, args = load_sdk()
if len(args) != 1:
    sys.exit('Use NEW_WORK')
work = Path(args[0]).absolute()
work.mkdir()
from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
import emberbsd_sdk.process as process
reuse = module('reuse-package-stage')
for name in ('source/build', 'recipe', 'sdk-recipe', 'stage-reference'):
    (work / name).mkdir(parents=True)
for name in ('source/source.dat', 'source/build/object.dat', 'recipe/patch', 'sdk-recipe/PLIST', 'abi.h', 'archive', 'full', 'runtime', 'devel'):
    (work / name).write_text('Typed fixture: ' + name)
value = dict(schema=2, version='23.1.3', target=dict(opsys='NetBSD', version='11.0', arch='aarch64', triple='aarch64--netbsd'),
    source=str(work / 'source'), build=str(work / 'source/build'), recipe=str(work / 'recipe'), sdk_recipe=str(work / 'sdk-recipe'),
    install_strip=True, flags={'CXXFLAGS': '-O2'}, cmake='/usr/bin/true', tar='/usr/bin/true', python=os.path.realpath(sys.executable),
    sdk_source=sdk, files=dict(compiler=[str(work / 'abi.h')], native_tools=['/usr/bin/true', os.path.realpath(sys.executable)],
    patches=[str(work / 'recipe/patch')], target_abi=[str(work / 'abi.h')]), manifests={n: str(work / n) for n in ('full', 'runtime', 'devel')},
    runtime=dict(archive=str(work / 'archive'), sha256=hashlib.sha256((work / 'archive').read_bytes()).hexdigest()))
config, receipt = work / 'inputs.json', work / 'receipt.json'
write_json(config, value)
checks, calls = [], []
mode = 'success'


def producer(command, log, *, env):
    calls.append(command)
    assert Path(reuse.quarantine_path(value)).is_file(), 'Producer started without a durable marker'
    stage = Path(env['DESTDIR']) / 'usr/pkg'
    stage.mkdir(parents=True)
    (stage / 'fixture.dat').write_bytes((work / 'source/build/object.dat').read_bytes())
    if mode == 'exit97':
        raise CommandError(97, command, log=log)
    if mode == 'uncertain':
        raise ProcessOwnershipError(12345, 'injected unknown session drain', log=log)


# These replacements isolate Ports recovery policy. Real process and full LLVM
# package validation remain separate acceptance tests.
process.run_logged = producer
reuse.validate_full_stage = lambda value, stage: reuse.check((Path(stage) / 'fixture.dat').is_file(), 'Missing typed fixture stage')
reuse.record(str(config), str(work / 'stage-reference'), str(receipt))
digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
original = reuse.snapshot(value)


def destination(name):
    path = work / name
    path.mkdir()
    return str(path)


def refused(label, operation, *arguments):
    count = len(calls)
    try:
        operation(*arguments)
    except Exception as error:
        assert 'quarantin' in str(error).lower(), f'{label}: wrong failure: {error}'
        assert len(calls) == count, f'{label}: started a producer'
        checks.append(label)
        return
    raise AssertionError(label + ': accepted a quarantined build')


mode = 'exit97'
try:
    reuse.install(str(config), str(receipt), digest, destination('failed-safe'))
except CommandError as error:
    assert error.returncode == 97
else:
    raise AssertionError('Completed producer failure was accepted')
reuse.verify(str(config), str(receipt), digest)
mode = 'success'
reuse.install(str(config), str(receipt), digest, destination('safe-retry'))
checks.append('completed exit97 allows a clean retry with unchanged inputs')
mode = 'uncertain'
try:
    reuse.install(str(config), str(receipt), digest, destination('failed-uncertain'))
except ProcessOwnershipError as error:
    assert error.sid == 12345
else:
    raise AssertionError('Uncertain producer was accepted')
refused('uncertain drain blocks verify', reuse.verify, str(config), str(receipt), digest)
refused('uncertain drain blocks install', reuse.install, str(config), str(receipt), digest, destination('blocked-install'))
refused('uncertain drain blocks new record', reuse.record, str(config), destination('blocked-record'), str(work / 'new-receipt.json'))
assert not (work / 'new-receipt.json').exists()
assert hashlib.sha256(receipt.read_bytes()).hexdigest() == digest and reuse.snapshot(value) == original
checks.append('quarantine is outside immutable trees and preserves the accepted receipt')
marker = reuse.quarantine_path(value)
assert Path(marker).is_file()
state = json.loads(Path(marker).read_text())
assert state['state'] == 'ownership-uncertain' and state['sid'] == 12345
alias = work / 'alias'
alias.symlink_to(work, target_is_directory=True)
aliased = copy.deepcopy(value)
for key in ('source', 'build', 'recipe', 'sdk_recipe'):
    aliased[key] = str(alias / Path(value[key]).relative_to(work))
write_json(work / 'alias-inputs.json', aliased)
refused('canonical ancestor alias keeps quarantine', reuse.record, str(work / 'alias-inputs.json'), destination('blocked-alias'), str(work / 'alias-receipt.json'))
old_build = Path(value['build'])
old_build.rename(old_build.with_name('renamed'))
renamed = dict(value, build=str(old_build.with_name('renamed')))
write_json(work / 'renamed-inputs.json', renamed)
refused('build inode rename keeps quarantine', reuse.record, str(work / 'renamed-inputs.json'), destination('blocked-rename'), str(work / 'renamed-receipt.json'))
old_build.with_name('renamed').rename(old_build)
# This fixture has no child processes. Removing its own marker tests corrupt
# marker refusals; production recovery requires an external drain audit.
Path(marker).unlink()
Path(marker).symlink_to(work / 'missing-marker-target')
refused('dangling marker refuses before producer', reuse.record, str(config), destination('blocked-link'), str(work / 'link-receipt.json'))
Path(marker).unlink()
Path(marker).write_text('not JSON')
refused('malformed marker refuses before producer', reuse.verify, str(config), str(receipt), digest)
write_json(work / 'results.json', dict(scope='Injected typed recovery policy only; no producer or LLVM package acceptance', checks=checks))
print(f'PASS: {len(checks)} typed recovery contracts; no SDK producers ran')
