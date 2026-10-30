#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise real host buildlink selection, reconfigure and stale-view handling."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'pkgsrc', 'host-prefix', 'stage-root', 'base-makeconf',
             'binding-record', 'bmake-mk', 'lock-root', 'work-parent'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
owner = Path(__file__).resolve().parents[1] / 'electron44'
with tempfile.TemporaryDirectory(prefix='electron-host-buildlink-test-', dir=a.work_parent) as temp:
    root = Path(temp)
    local = root / 'consumer/files'; local.mkdir(parents=True)
    for name in ('build-electron.py', 'host-buildlink.py'):
        shutil.copy2(owner / 'files' / name, local / name)
    shutil.copytree(owner / 'files/host-buildlink', local / 'host-buildlink')
    deps = local.parent / 'host-dependencies.mk'
    shutil.copy2(owner / 'host-dependencies.mk', deps)
    spec = importlib.util.spec_from_file_location('build_electron_test', local / 'build-electron.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    sdk = module.load_sdk(a.sdk_source)
    native = sdk['host_prefix'].load_host_prefix(a.host_prefix, required_roles=('make', 'python'),
                                                compiler_family='clang')
    options = SimpleNamespace(work=root, phase='configure', sdk_source=a.sdk_source,
        host_prefix=a.host_prefix, host_buildlink_pkgsrc=a.pkgsrc,
        host_buildlink_stage_root=a.stage_root, host_buildlink_base_makeconf=a.base_makeconf,
        host_buildlink_bmake_mk=a.bmake_mk, lock_root=a.lock_root)
    binding = {'cxx': str(a.binding_record.parent / 'cxx')}
    def select():
        env = sdk['process'].sanitized_environment()
        view = module.host_buildlink(options, sdk, native, env, binding)
        return Path(view), env
    first, env = select()
    assert (first / 'lib/pkgconfig/protobuf.pc').is_file()
    config = root / 'configuration.json'
    config.write_text(json.dumps({'environment': env}))
    options.phase = 'reconfigure'
    second, same_env = select()
    assert second == first and same_env == env
    deps.write_text(deps.read_text() + '\n# changed declaration\n')
    options.phase = 'build'
    try:
        select()
        raise AssertionError('build accepted stale selection')
    except ValueError as error:
        assert 'reconfigure before building' in str(error)
    options.phase = 'reconfigure'
    third, changed_env = select()
    assert third != first and (third / 'lib/pkgconfig/protobuf.pc').is_file()
    config.write_text(json.dumps({'environment': changed_env}))
    link = third / 'lib/pkgconfig/protobuf.pc'
    link.unlink()
    fourth, _ = select()
    assert fourth != third and (fourth / 'lib/pkgconfig/protobuf.pc').is_file()
    config.write_text(json.dumps({'environment': _}))
    local_archive = fourth / 'lib/libffi.la'
    assert local_archive.is_file() and not local_archive.is_symlink()
    local_archive.write_text(local_archive.read_text() + '\n# changed local view\n')
    fifth, fifth_env = select()
    assert fifth != fourth
    config.write_text(json.dumps({'environment': fifth_env}))
    fourth = fifth
    (fourth / 'directory-link').symlink_to(fourth / 'include', target_is_directory=True)
    try:
        select()
        raise AssertionError('accepted untracked directory symlink')
    except sdk['process'].CommandError as error:
        assert b'directory symlinks are unsupported' in error.stderr
    (fourth / 'directory-link').unlink()
    deps.write_text(deps.read_text() + '\nDEPENDS+= electron-missing-provider>=1:../../devel/zlib\n')
    try:
        select()
        raise AssertionError('buildlink installed an unavailable dependency')
    except sdk['process'].CommandError:
        pass
print('PASS: actual host buildlink reconfigure and stale selection')
