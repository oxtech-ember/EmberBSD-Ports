#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check additive generated host wrapper metadata without accepting replacements."""
import argparse
import importlib.util
import hashlib
import json
import subprocess
import tempfile
from types import SimpleNamespace
from pathlib import Path

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/host-buildlink.py'
parser = argparse.ArgumentParser(); parser.add_argument('--ninja', type=Path, required=True)
ninja = parser.parse_args().ninja.resolve(strict=True)
spec = importlib.util.spec_from_file_location('host', owner)
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
old, new, prefix = Path('/old'), Path('/new'), Path('/selected')
before = b'BUILDLINK_PREFIX.old=\t/selected\n_BLNK_PKG_DBDIR.old=\t/selected/pkgdb/old-1\n'
extra = b'BUILDLINK_PREFIX.new=\t/selected\n_BLNK_PKG_DBDIR.new=\t/selected/pkgdb/new-1\n'
inputs = {'/selected/pkgdb/new-1/+CONTENTS': 'hash'}
assert host._additive_wrapper(before, before + extra, old, new, prefix, inputs) == before + extra
for changed in (before.replace(b'old-1', b'old-2') + extra,
                before + extra.replace(b'/selected/pkgdb/new-1', b'/foreign/pkgdb/new-1'),
                before + extra.splitlines(keepends=True)[0], before + b'OTHER=yes\n',
                before + b'BUILDLINK_PREFIX.old=\t/selected\n'):
    try:
        host._additive_wrapper(before, changed, old, new, prefix, inputs)
    except ValueError:
        pass
    else:
        raise AssertionError('accepted incompatible wrapper')
print('PASS: paired additive provider metadata and incompatible changes')

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory).resolve(); prefix = root / 'prefix'; prefix.mkdir()
    target = prefix / 'old.h'; target.write_text('old header')
    added_target = prefix / 'new.h'; added_target.write_text('new header')
    db = prefix / 'pkgdb/new-1/+CONTENTS'; db.parent.mkdir(parents=True); db.write_text('package')
    base = root / 'base'; base.write_text('base')
    binding = root / 'binding'; binding.write_text('binding')
    work, candidate = root / 'old-work', root / 'new-work'
    rel = Path('objects/devel/electron-host-context/work/.buildlink')
    wrapper_rel = rel.parent / '.wrapper_makevars.mk'
    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    identities = []
    for index, path in enumerate((work, candidate)):
        view = path / rel; view.mkdir(parents=True)
        (view / 'include').mkdir(); (view / 'include/old.h').symlink_to(target)
        if index: (view / 'include/new.h').symlink_to(added_target)
        wrapper = path / wrapper_rel
        (path / 'make.conf').write_text('same configuration\n')
        content = f'BUILDLINK_PREFIX.old=\t{prefix}\n_BLNK_PKG_DBDIR.old=\t{prefix}/pkgdb/old-1\n'
        if index: content += f'BUILDLINK_PREFIX.new=\t{prefix}\n_BLNK_PKG_DBDIR.new=\t{db.parent}\n'
        wrapper.write_text(content)
        if index: (view / '.buildlink_new_done').write_text('')
        inputs = {str(file): digest(file) for file in (target, base, binding, wrapper, path / 'make.conf')}
        links = {'include/old.h': str(target)}
        if index:
            inputs.update({str(file): digest(file) for file in (added_target, db, view / '.buildlink_new_done')})
            links['include/new.h'] = str(added_target)
        identities.append({'inputs': inputs, 'links': links})
    inv = {'work': str(work), 'base_makeconf': str(base), 'binding_record': str(binding)}
    cinv = {**inv, 'work': str(candidate), 'shared_cpuinfo': 'yes'}
    new_inv = {**inv, 'shared_cpuinfo': 'yes'}
    saved = {'identity': identities[0], 'invocation': inv}
    current = json.loads(json.dumps(identities[0])); current['inputs'][str(db)] = digest(db)
    plan = host._extension_plan(saved, current, identities[1], new_inv, cinv, work, candidate, prefix)
    host._canonical_work(work, required=True)
    alias = root / 'alias'; alias.symlink_to(candidate, target_is_directory=True)
    try: host._canonical_work(alias, required=True)
    except ValueError: pass
    else: raise AssertionError('symlink candidate accepted')
    for rel_path in ('make.conf', wrapper_rel):
        changed_path = candidate / rel_path; old_mode = changed_path.stat().st_mode & 0o777
        changed_path.chmod(old_mode ^ 0o100)
        try: host._extension_plan(saved, current, identities[1], new_inv, cinv, work, candidate, prefix)
        except ValueError: pass
        else: raise AssertionError('changed generated file mode accepted')
        finally: changed_path.chmod(old_mode)
    candidate_wrapper = candidate / wrapper_rel
    wrapper_bytes = candidate_wrapper.read_bytes(); wrapper_mode = candidate_wrapper.stat().st_mode & 0o777
    candidate_wrapper.unlink(); candidate_wrapper.symlink_to(work / wrapper_rel)
    try: host._extension_plan(saved, current, identities[1], new_inv, cinv, work, candidate, prefix)
    except ValueError: pass
    else: raise AssertionError('generated wrapper symlink accepted')
    finally:
        candidate_wrapper.unlink(); candidate_wrapper.write_bytes(wrapper_bytes); candidate_wrapper.chmod(wrapper_mode)
    for case in ('header', 'link', 'binding'):
        bad = json.loads(json.dumps(identities[1])); bad_inv = dict(cinv)
        if case == 'header': bad['inputs'][str(target)] = 'changed'
        if case == 'link': bad['links']['include/old.h'] = str(added_target)
        if case == 'binding': bad_inv['binding_record'] = '/foreign'
        try: host._extension_plan(saved, current, bad, new_inv, bad_inv, work, candidate, prefix)
        except ValueError: pass
        else: raise AssertionError('accepted changed ' + case)
    old_stat = (work / rel / 'include/old.h').lstat()
    # Exercise Ninja's real timestamp/dependency behavior with the retained path.
    build = root / 'build.ninja'
    build.write_text('rule copy\n  command = /bin/cp $in $out\nbuild object: copy ' +
                     str(work / rel / 'include/old.h') + '\n')
    subprocess.run([str(ninja), '-C', str(root), 'object'], check=True, capture_output=True)
    obj = root / 'object'; object_before = obj.stat().st_mtime_ns
    atomic = host._atomic_file
    def interrupted(path, *args, **kwargs):
        if path.name == '.buildlink_new_done':
            raise OSError('simulated interruption')
        return atomic(path, *args, **kwargs)
    host._atomic_file = interrupted
    try: host._apply_extension(work, candidate, *plan, saved, identities[1])
    except OSError: pass
    else: raise AssertionError('simulated interruption did not occur')
    finally: host._atomic_file = atomic
    assert (work / '.host-buildlink-extension.json').is_file()
    assert (work / rel / 'include/new.h').is_symlink()
    partial = json.loads(json.dumps(current)); partial['links']['include/new.h'] = str(added_target)
    partial['inputs'][str(added_target)] = digest(added_target)
    retry_partial = host._extension_plan(saved, partial, identities[1], new_inv, cinv, work, candidate, prefix, recovery=True)
    assert retry_partial == plan
    host._apply_extension(work, candidate, *retry_partial, saved, identities[1])
    assert (work / rel / 'include/new.h').resolve() == added_target
    assert (work / rel / '.buildlink_new_done').read_text() == ''
    assert (work / rel / 'include/old.h').lstat().st_mtime_ns == old_stat.st_mtime_ns
    result = subprocess.run([str(ninja), '-C', str(root), 'object'], check=True, capture_output=True, text=True)
    assert 'no work to do' in result.stdout and obj.stat().st_mtime_ns == object_before
    # Repeating the same journaled plan is safe after any completed operation.
    recovered = json.loads(json.dumps(current))
    recovered['links']['include/new.h'] = str(added_target)
    recovered['inputs'][str(work / wrapper_rel)] = digest(work / wrapper_rel)
    recovered['inputs'][str(work / rel / '.buildlink_new_done')] = digest(work / rel / '.buildlink_new_done')
    recovered['inputs'][str(added_target)] = digest(added_target)
    recovered['inputs'][str(db)] = digest(db)
    retry = host._extension_plan(saved, recovered, identities[1], new_inv, cinv, work, candidate, prefix, recovery=True)
    assert retry == plan
    assert host._extension_identity(recovered, work) == host._extension_identity(identities[1], candidate)
    host._apply_extension(work, candidate, *retry, saved, identities[1])
    new_link = work / rel / 'include/new.h'
    new_link.unlink(); new_link.symlink_to(target)
    try: host._apply_extension(work, candidate, *retry, saved, identities[1])
    except ValueError: pass
    else: raise AssertionError('foreign extension link accepted')
    new_link.unlink(); new_link.symlink_to(added_target)
    journal = work / '.host-buildlink-extension.json'
    altered = json.loads(journal.read_text()); altered['candidate'] = '/foreign'
    journal.write_text(json.dumps(altered))
    try: host._apply_extension(work, candidate, *plan, saved, identities[1])
    except ValueError: pass
    else: raise AssertionError('foreign extension journal accepted')
print('PASS: additive link/file transaction, unchanged links and interrupted retry')

controller_path = owner.with_name('build-electron.py')
spec = importlib.util.spec_from_file_location('electron', controller_path)
controller = importlib.util.module_from_spec(spec); spec.loader.exec_module(controller)
class CommandError(Exception):
    def __init__(self, returncode): self.returncode = returncode
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory).resolve(); old = root / 'host-buildlink-0'; old.mkdir()
    (root / 'configuration.json').write_text(json.dumps({'environment': {'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK': str(old)}}))
    calls = []; race = [False]
    def capture(command, env):
        calls.append(command)
        context = Path(command[command.index('--work') + 1])
        if '--check' in command: raise CommandError(3)
        if '--extend-from' in command:
            if race[0]:
                (old / '.host-buildlink-extension.json').write_text('{}')
                raise CommandError(3)
            return SimpleNamespace(stdout=str(old / 'view').encode())
        context.mkdir(); return SimpleNamespace(stdout=str(context / 'view').encode())
    sdk = {'process': SimpleNamespace(capture=capture, CommandError=CommandError)}
    native = SimpleNamespace(tool=lambda role: '/selected/' + role)
    options = SimpleNamespace(work=root, sdk_source=Path('/sdk'), host_prefix=Path('/prefix'),
                              host_buildlink_pkgsrc=Path('/export'), host_buildlink_stage_root=None,
                              host_buildlink_base_makeconf=Path('/makeconf'), host_buildlink_bmake_mk=Path('/mk'),
                              lock_root=Path('/lock'), phase='reconfigure')
    environment = {}
    assert controller.host_buildlink(options, sdk, native, environment, {'cxx': '/binding/cxx'}) == str(old / 'view')
    assert environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] == str(old)
    assert len(calls) == 3 and '--extend-from' in calls[-1]
    (old / '.host-buildlink-extension.json').write_text(json.dumps({'candidate': str(root / 'host-buildlink-1')}))
    calls.clear()
    assert controller.host_buildlink(options, sdk, native, {}, {'cxx': '/binding/cxx'}) == str(old / 'view')
    assert len(calls) == 1 and '--extend-from' in calls[0]
    options.phase = 'build'
    try: controller.host_buildlink(options, sdk, native, {}, {'cxx': '/binding/cxx'})
    except ValueError: pass
    else: raise AssertionError('build resumed a pending extension')
    (old / '.host-buildlink-extension.json').unlink(); options.phase = 'reconfigure'; race[0] = True
    try: controller.host_buildlink(options, sdk, native, {}, {'cxx': '/binding/cxx'})
    except ValueError: pass
    else: raise AssertionError('fallback accepted a newly pending journal')
print('PASS: controller retains the old path and resumes only during reconfigure')
