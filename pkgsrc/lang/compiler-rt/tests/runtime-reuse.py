#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise runtime source-equivalence reuse and meaningful refusals."""
import copy
import importlib.util
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import types

files = Path(__file__).resolve().parents[1] / 'files'
sys.path.insert(0, str(files))
spec = importlib.util.spec_from_file_location('runtime', files / 'runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

class Failure(Exception):
    pass

def require(value, message):
    if not value:
        raise Failure(message)

old_files = {'pkgsrc/lang/compiler-rt/files/source.py': 'old',
             'pkgsrc/lang/llvm/version.mk': 'old',
             'pkgsrc/lang/llvm/distinfo': 'old broad inventory', 'patch': 'same'}
expected = {'files': dict(old_files, **{'pkgsrc/lang/compiler-rt/files/source.py': 'new',
    'pkgsrc/lang/llvm/version.mk': 'new', 'pkgsrc/lang/compiler-rt/files/runtime.py': 'new',
    'pkgsrc/lang/compiler-rt/files/build.py': 'same'})}
expected['files'].pop('pkgsrc/lang/llvm/distinfo')
cli_bytes = (files / 'runtime.py').read_bytes()
cli_hash = hashlib.sha256(cli_bytes).hexdigest()
stage = {'recipe': {'ports_revision': 'a' * 40, 'files': dict(old_files, **{'pkgsrc/lang/compiler-rt/files/runtime.py': cli_hash,
    'pkgsrc/lang/compiler-rt/files/build.py': 'same'})}}
source = {'format': 'emberbsd-llvm-source', 'version': 1, 'llvm_version': '23',
          'components': ['llvm'], 'source': {'archive': 'llvm', 'sha512': 'abc'},
          'recipe': {'files': old_files}, 'tree_sha256': 'payload'}
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / 'llvm-source.json').write_text(json.dumps(source))
    owner = types.SimpleNamespace(require=require, SOURCE_MANIFEST='llvm-source.json', PORTS=root,
        NON_OUTPUT_INPUTS={'pkgsrc/lang/compiler-rt/files/source.py',
                           'pkgsrc/lang/llvm/distinfo'},
        digest=lambda value: hashlib.sha256(value).hexdigest(),
        process=types.SimpleNamespace(capture=lambda *a, **k: types.SimpleNamespace(stdout=cli_bytes),
                                      sanitized_environment=lambda: {}),
        paths=types.SimpleNamespace(canonical_existing=lambda p: str(Path(p).resolve(strict=True))),
        jsonio=types.SimpleNamespace(read_json=lambda p: json.loads(p.read_text())),
        tree_hash=lambda p: 'payload', verify_source=lambda p, git: source)
    def check(record, want_error=False, current=expected):
        try:
            runtime.compatible_source(owner, record, current, str(root), str(root), '/git')
        except Failure:
            assert want_error
        else:
            assert not want_error
    check(stage)
    guard = b"    if args.command in ('build', 'verify') and args.target == 'riscv32' and args.phase == 'full':\n        cli.error('riscv32 supports only builtins and bootstrap')\n"
    assert guard in cli_bytes
    assert runtime.build_cli(cli_bytes) == runtime.build_cli(cli_bytes.replace(guard, b''))
    target_old = cli_bytes.replace(b"choices=('aarch64', 'amd64', 'riscv32')", b"choices=('aarch64', 'amd64')")
    assert runtime.build_cli(cli_bytes, 'aarch64') == runtime.build_cli(target_old, 'aarch64')
    assert runtime.build_cli(cli_bytes, 'riscv32') != runtime.build_cli(target_old, 'riscv32')
    assert runtime.build_cli(cli_bytes, 'aarch64') != runtime.build_cli(cli_bytes.replace(b"default='clang'", b"default='gcc'"), 'aarch64')
    assert runtime.build_cli(cli_bytes) != runtime.build_cli(cli_bytes.replace(b"default='clang'", b"default='gcc'"))
    assert runtime.build_cli(cli_bytes) != runtime.build_cli(cli_bytes.replace(b"args.command == 'build'", b"args.command == 'other'"))
    assert runtime.build_cli(cli_bytes) != runtime.build_cli(cli_bytes.replace(b"    if args.command == 'prepare':", b"    args.host_compiler_family = 'gcc'\n    if args.command == 'prepare':"))
    altered = copy.deepcopy(stage)
    altered['recipe']['files']['patch'] = 'changed'
    check(altered, True)
    altered = copy.deepcopy(stage)
    altered['recipe']['files']['pkgsrc/lang/compiler-rt/files/build.py'] = 'changed'
    check(altered, True)
    # The recorded digests identify both trees; neither is hashed again.
    owner.tree_hash = lambda p: (_ for _ in ()).throw(AssertionError('prepared source hashed again'))
    check(stage)
    tampered = dict(source, tree_sha256='tampered')
    (root / 'llvm-source.json').write_text(json.dumps(tampered))
    check(stage, True)
    changed = copy.deepcopy(source)
    changed['source']['sha512'] = 'different'
    (root / 'llvm-source.json').write_text(json.dumps(changed))
    check(stage, True)
rv = b"    if definition['arch'] == 'riscv32':\n        driver_flags += ['-march=rv32imac_zicsr_zifencei', '-mabi=ilp32']\n"
old_build = b'def cmake_arguments(definition):\n    driver_flags = []\n    return driver_flags\n'
new_build = old_build.replace(b'    return driver_flags\n', rv + b'    return driver_flags\n')
assert runtime.compatible_build_for_target(old_build, new_build, 'aarch64')
assert runtime.compatible_build_for_target(old_build, new_build, 'amd64')
assert not runtime.compatible_build_for_target(old_build, new_build, 'riscv32')
assert not runtime.compatible_build_for_target(old_build, new_build + b'changed\n', 'aarch64')
mutated = new_build.replace(rv, b"    definition['arch'] = 'riscv32'\n" + rv)
assert not runtime.compatible_build_for_target(mutated, mutated, 'aarch64')
assert not runtime.compatible_build_for_target(old_build, new_build.replace(b'riscv32', b'aarch64'), 'aarch64')
assert not runtime.compatible_build_for_target(old_build, new_build.replace(rv, b"    if definition['arch'] == 'riscv32':\n        unrelated = 1\n"), 'aarch64')
assert not runtime.compatible_build_for_target(old_build, new_build.replace(rv, b"    if definition['arch'] == 'riscv32':\n        yield 1\n"), 'aarch64')
assert not runtime.compatible_build_for_target(old_build, new_build.replace(b'def cmake_arguments(definition):', b'def cmake_arguments():'), 'aarch64')

# Exporting the same selected pkgsrc recipe changed only how build.py records
# its own input paths and revision.  Normalize that exact metadata transition,
# while keeping compiler settings and source hashes part of the comparison.
recording_old = (b"def cmake_arguments(definition):\n"
    b"    return ['-DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON']\n\n"
    b"def effective_recipe(owner, prepared, git):\n"
    b"    files = dict(prepared['recipe']['files'])\n"
    b"    for path in selected:\n"
    b"        files[str(path.relative_to(owner.PORTS))] = owner.inventory.sha256_file(path)\n"
    b"    return dict(ports_revision=owner.git_revision(git, owner.PORTS), files=files)\n")
recording_new = recording_old.replace(
    b"files[str(path.relative_to(owner.PORTS))] = owner.inventory.sha256_file(path)",
    b"files[owner.input_name(path)] = owner.inventory.sha256_file(path)").replace(
    b"return dict(ports_revision=owner.git_revision(git, owner.PORTS), files=files)",
    b"revision = None if owner.EXPORTED else owner.git_revision(git, owner.PORTS)\n"
    b"    return dict(ports_revision=revision, files=files)")
assert runtime.compatible_build_for_target(recording_old, recording_new, 'riscv32')
assert not runtime.compatible_build_for_target(recording_old,
    recording_new.replace(b"COMPILER_RT_DEFAULT_TARGET_ONLY=ON",
                          b"COMPILER_RT_DEFAULT_TARGET_ONLY=OFF"), 'riscv32')
assert not runtime.compatible_build_for_target(recording_old,
    recording_new.replace(b"owner.input_name(path)", b"owner.input_name(other)"), 'riscv32')

old_settings = (b"def cmake_arguments(definition, phase):\n    settings = {}\n"
                b"    if phase == 'builtins':\n"
                b"        settings.update(COMPILER_RT_DEFAULT_TARGET_ONLY='ON')\n"
                b"    return settings\n")
rv_settings = (b"        if definition['arch'] == 'riscv32':\n"
               b"            settings.update(COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN='ON',\n"
               b"                            COMPILER_RT_BUILD_STANDALONE_LIBATOMIC='OFF')\n")
new_settings = old_settings.replace(b"        settings.update(COMPILER_RT_DEFAULT_TARGET_ONLY='ON')\n",
    rv_settings + b"        settings.update(COMPILER_RT_DEFAULT_TARGET_ONLY='ON')\n")
assert runtime.compatible_build_for_target(old_settings, new_settings, 'aarch64')
assert not runtime.compatible_build_for_target(old_settings, new_settings, 'riscv32')
assert runtime.compatible_build_for_target(old_settings, new_settings, 'riscv32',
                                          atomic_defaults=True)
assert not runtime.compatible_build_for_target(old_settings, new_settings.replace(
    b"COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN='ON'", b"COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN='OFF'"),
    'riscv32', atomic_defaults=True)
assert not runtime.compatible_build_for_target(old_settings, new_settings.replace(
    b"COMPILER_RT_BUILD_STANDALONE_LIBATOMIC='OFF'", b"COMPILER_RT_BUILD_STANDALONE_LIBATOMIC='ON'"),
    'riscv32', atomic_defaults=True)
assert not runtime.compatible_build_for_target(old_settings,
    new_settings.replace(b"'riscv32'", b"'aarch64'"), 'aarch64')
old_shadow = (b"def cmake_arguments(definition):\n    settings = {}\n"
              b"    def helper(definition):\n        return definition['arch']\n"
              b"    return settings\n")
shadow_guard = (b"        if definition['arch'] == 'riscv32':\n"
                b"            settings.update(EXAMPLE='ON')\n")
new_shadow = old_shadow.replace(b"        return definition['arch']\n",
    shadow_guard + b"        return definition['arch']\n")
assert not runtime.compatible_build_for_target(old_shadow, new_shadow, 'aarch64')
unguarded_settings = old_settings.replace(b"        settings.update(COMPILER_RT_DEFAULT_TARGET_ONLY='ON')\n",
    b"        settings.update(COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN='ON')\n"
    b"        settings.update(COMPILER_RT_DEFAULT_TARGET_ONLY='ON')\n")
assert not runtime.compatible_build_for_target(old_settings, unguarded_settings, 'aarch64')

print('runtime source reuse, target guards and CLI: PASS')

# Both sides of a changed patch must be confined to non-bootstrap libc++.
locale_patch = b'--- a/libcxx/include/locale\n+++ b/libcxx/include/locale\n@@ -1 +1 @@\n-a\n+b\n'
assert runtime.libcxx_only_patch(locale_patch)
assert runtime.patch_paths(b'--- a/libcxx/include/a\n+++ b/libcxx/include/b\n') is None
assert not runtime.libcxx_only_patch(locale_patch + b'--- a/libunwind/src/a\n+++ b/libunwind/src/a\n')
assert not runtime.libcxx_only_patch(b'--- a/libcxx/../libunwind/a\n+++ b/libcxx/../libunwind/a\n')
assert not runtime.libcxx_only_patch(b'--- a/libcxx/a\n+++ b/runtimes/CMakeLists.txt\n')
assert not runtime.libcxx_only_patch(b'not a unified patch')
assert not runtime.libcxx_only_patch(b'--- a/libcxx/CMakeLists.txt\n+++ b/libcxx/CMakeLists.txt\n')

# Exercise the actual compatibility helper, including stage phase and digests.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    patch = root / 'patches' / 'patch-locale'
    patch.parent.mkdir()
    patch.write_bytes(locale_patch)
    dist = root / 'distinfo'
    old_dist = b'SHA512 (llvm.tar.xz) = fixed\n'
    new_dist = old_dist + b'SHA1 (patch-locale) = checked\n'
    dist.write_bytes(new_dist)
    digest = lambda data: hashlib.sha256(data).hexdigest()
    prefix = 'pkgsrc/lang/compiler-rt/'
    patch_name = prefix + 'patches/patch-locale'
    dist_name = prefix + 'distinfo'
    old_recipe = {dist_name: digest(old_dist)}
    original = dict(source, recipe={'files': old_recipe}, tree_sha256='old')
    current_source = dict(original, tree_sha256='new')
    (root / 'llvm-source.json').write_text(json.dumps(original))
    previous = {'recipe': {'ports_revision': 'a' * 40,
        'files': dict(old_recipe, **{prefix+'files/runtime.py': cli_hash,
                                   prefix+'files/build.py': 'same'})},
        'components': ['builtins', 'libunwind-static']}
    future = {'files': dict(previous['recipe']['files'], **{dist_name: digest(new_dist),
                                                             patch_name: digest(locale_patch)})}
    def capture(command, **kwargs):
        name = command[-1].split(':', 1)[-1]
        values = {dist_name: old_dist, prefix+'files/runtime.py': cli_bytes}
        return types.SimpleNamespace(stdout=values[name])
    test_owner = types.SimpleNamespace(require=require, SOURCE_MANIFEST='llvm-source.json',
        NON_OUTPUT_INPUTS={'pkgsrc/lang/compiler-rt/files/source.py',
                           'pkgsrc/lang/llvm/distinfo'},
        PORTS=root, OWNER=root, digest=digest, read=lambda p: p.read_bytes(),
        process=types.SimpleNamespace(capture=capture, sanitized_environment=lambda: {}),
        paths=types.SimpleNamespace(canonical_existing=lambda p: str(Path(p).resolve(strict=True))),
        jsonio=types.SimpleNamespace(read_json=lambda p: json.loads(p.read_text())),
        verify_source=lambda p, git: current_source)
    def phase_check(record, selected, fail=False):
        try:
            runtime.compatible_source(test_owner, record, selected, str(root), str(root), '/git')
        except Failure:
            assert fail
        else:
            assert not fail
    phase_check(previous, future)
    full = copy.deepcopy(previous)
    full['components'].append('libcxx')
    phase_check(full, future, True)
    missing = copy.deepcopy(future)
    del missing['files'][dist_name]
    phase_check(previous, missing, True)
    dist.write_bytes(new_dist.replace(b'fixed', b'other'))
    bad = copy.deepcopy(future)
    bad['files'][dist_name] = digest(dist.read_bytes())
    phase_check(previous, bad, True)
    dist.write_bytes(new_dist)
    for path in (b'libunwind/src/a', b'compiler-rt/lib/builtins/a', b'runtimes/CMakeLists.txt'):
        unsafe = b'--- a/' + path + b'\n+++ b/' + path + b'\n'
        patch.write_bytes(unsafe)
        bad = copy.deepcopy(future)
        bad['files'][patch_name] = digest(unsafe)
        phase_check(previous, bad, True)
    patch.write_bytes(locale_patch)

    # Exercise changed old and new profile patch blobs, not just names.
    def patch_for(path):
        return b'--- a/' + path + b'\n+++ b/' + path + b'\n@@ -1 +1 @@\n-old\n+new\n'
    profile_path = b'compiler-rt/lib/profile/InstrProfilingValue.c'
    profile_old = patch_for(profile_path)
    profile_new = profile_old + patch_for(b'compiler-rt/include/profile/InstrProfData.inc')
    profile_name = prefix + 'patches/patch-profile'
    profile_file = root / 'patches/patch-profile'
    profile_file.write_bytes(profile_new)
    profile_old_dist = old_dist + b'SHA1 (patch-profile) = old\n'
    profile_new_dist = old_dist + b'SHA1 (patch-profile) = new\n'
    dist.write_bytes(profile_new_dist)
    original = dict(source, recipe={'files': {dist_name: digest(profile_old_dist),
                                             profile_name: digest(profile_old)}}, tree_sha256='old')
    current_source = dict(original, tree_sha256='new')
    (root / 'llvm-source.json').write_text(json.dumps(original))
    previous = {'recipe': {'ports_revision': 'a' * 40,
        'files': {dist_name: digest(profile_old_dist), profile_name: digest(profile_old),
                  prefix+'files/runtime.py': cli_hash, prefix+'files/build.py': 'same'}},
        'components': ['builtins', 'libunwind-static']}
    future = {'files': dict(previous['recipe']['files'], **{
        dist_name: digest(profile_new_dist), profile_name: digest(profile_new)})}
    def capture_profile(command, **kwargs):
        name = command[-1].split(':', 1)[-1]
        values = {dist_name: profile_old_dist, profile_name: profile_old,
                  prefix+'files/runtime.py': cli_bytes}
        return types.SimpleNamespace(stdout=values[name])
    test_owner.process.capture = capture_profile
    for components in (['builtins'], ['builtins', 'libunwind-static'],
                       ['builtins', 'libunwind', 'libcxxabi', 'libcxx']):
        record = copy.deepcopy(previous)
        record['components'] = components
        phase_check(record, future)
    for components in ([], ['builtins', 'profile'], ['libcxx'], ['builtins', 'builtins'], None):
        record = copy.deepcopy(previous)
        record['components'] = components
        phase_check(record, future, True)
    for forbidden in (b'compiler-rt/lib/builtins/atomic.c', b'cmake/CMakeLists.txt',
                      b'compiler-rt/include/profile/other.h',
                      b'compiler-rt/lib/profile/CMakeLists.txt'):
        bad_blob = profile_new + patch_for(forbidden)
        profile_file.write_bytes(bad_blob)
        bad = copy.deepcopy(future)
        bad['files'][profile_name] = digest(bad_blob)
        phase_check(previous, bad, True)
    profile_file.write_bytes(profile_new)
    # Historic side must be checked independently of a safe current side.
    bad_old = profile_old + patch_for(b'compiler-rt/lib/builtins/atomic.c')
    bad_previous = copy.deepcopy(previous)
    bad_previous['recipe']['files'][profile_name] = digest(bad_old)
    original['recipe']['files'][profile_name] = digest(bad_old)
    (root / 'llvm-source.json').write_text(json.dumps(original))
    def capture_bad_old(command, **kwargs):
        if command[-1].endswith(':' + profile_name):
            return types.SimpleNamespace(stdout=bad_old)
        return capture_profile(command, **kwargs)
    test_owner.process.capture = capture_bad_old
    phase_check(bad_previous, future, True)
    test_owner.process.capture = capture
    atomic_patch = (b'--- a/compiler-rt/lib/builtins/atomic.c\n'
                    b'+++ b/compiler-rt/lib/builtins/atomic.c\n'
                    b'@@ -1 +1,2 @@\n'
                    b' unchanged\n'
                    b'+/* RV32-only atomic selection. */\n')
    atomic_dist = (old_dist + b'SHA1 (patch-07-atomic-width-selection) = checked\n'
                   b'SHA1 (patch-08-atomic-rv32-libc-provider) = checked\n')
    dist.write_bytes(atomic_dist)
    atomic_name = 'pkgsrc/lang/compiler-rt/patches/patch-07-atomic-width-selection'
    atomic_second_name = 'pkgsrc/lang/compiler-rt/patches/patch-08-atomic-rv32-libc-provider'
    atomic_file = root / 'patches' / Path(atomic_name).name
    atomic_file.write_bytes(atomic_patch)
    atomic_second_patch = atomic_patch + b'--- a/compiler-rt/lib/builtins/atomic.c\n+++ b/compiler-rt/lib/builtins/atomic.c\n@@ -4 +5 @@\n unchanged\n+/* second selected atomic hunk */\n'
    atomic_second_file = root / 'patches' / Path(atomic_second_name).name
    atomic_second_file.write_bytes(atomic_second_patch)
    atomic_dist_hash = digest(atomic_dist)
    atomic_patch_hash = digest(atomic_patch)
    atomic_second_hash = digest(atomic_second_patch)
    original = dict(source, recipe={'files': {dist_name: digest(old_dist)}}, tree_sha256='old')
    current_source = dict(original, recipe={'files': {dist_name: atomic_dist_hash,
        atomic_name: atomic_patch_hash}}, tree_sha256='new')
    (root / 'llvm-source.json').write_text(json.dumps(original))
    previous = {'recipe': {'ports_revision': 'a' * 40,
        'files': {dist_name: digest(old_dist), prefix+'files/runtime.py': cli_hash,
                  prefix+'files/build.py': 'same'}},
        'components': ['builtins', 'libunwind-static'], 'target': 'aarch64',
        'machine_arch': 'aarch64'}
    future = {'files': dict(previous['recipe']['files'], **{
        dist_name: atomic_dist_hash, atomic_name: atomic_patch_hash,
        atomic_second_name: atomic_second_hash})}
    current_source['recipe']['files'][atomic_second_name] = atomic_second_hash
    phase_check(previous, future)
    full = copy.deepcopy(previous)
    full['components'] = ['builtins', 'libunwind', 'libcxxabi', 'libcxx']
    phase_check(full, future)
    riscv = copy.deepcopy(previous)
    riscv['target'] = 'riscv32'
    riscv['machine_arch'] = 'riscv32'
    cmake_file = root / 'compiler-rt/lib/builtins/CMakeLists.txt'
    cmake_file.parent.mkdir(parents=True, exist_ok=True)
    cmake_defaults = (b'option(COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN\n'
                      b'  "Skip the atomic builtin"\n'
                      b'  On)\n'
                      b'option(COMPILER_RT_BUILD_STANDALONE_LIBATOMIC\n'
                      b'  "Build standalone shared atomic library."\n'
                      b'  OFF)\n')
    cmake_file.write_bytes(cmake_defaults)
    assert runtime.atomic_builtin_excluded(riscv, root, root)
    phase_check(riscv, future)
    riscv_full = copy.deepcopy(riscv)
    riscv_full['components'].append('libcxx')
    phase_check(riscv_full, future, True)
    cmake_file.write_bytes(cmake_defaults.replace(b'  On)', b'  Off)'))
    assert not runtime.atomic_builtin_excluded(riscv, root, root)
    phase_check(riscv, future, True)
    cmake_file.write_bytes(cmake_defaults.replace(b'  OFF)', b'  ON)'))
    assert not runtime.atomic_builtin_excluded(riscv, root, root)
    phase_check(riscv, future, True)
    cmake_file.write_bytes(cmake_defaults)
    other_file_patch = atomic_patch + b'--- a/compiler-rt/lib/builtins/absvdi2.c\n+++ b/compiler-rt/lib/builtins/absvdi2.c\n@@ -1 +1,2 @@\n unchanged\n+changed\n'
    atomic_file.write_bytes(other_file_patch)
    mixed = copy.deepcopy(future)
    mixed['files'][atomic_name] = digest(other_file_patch)
    current_source['recipe']['files'][atomic_name] = digest(other_file_patch)
    phase_check(previous, mixed, True)
    non_atomic_patch = atomic_patch.replace(b'compiler-rt/lib/builtins/atomic.c',
        b'compiler-rt/lib/builtins/absvdi2.c')
    atomic_file.write_bytes(non_atomic_patch)
    rejected = copy.deepcopy(future)
    rejected['files'][atomic_name] = digest(non_atomic_patch)
    current_source['recipe']['files'][atomic_name] = digest(non_atomic_patch)
    phase_check(previous, rejected, True)

# A changed build command cannot disappear through preflight normalization.
assert not runtime.compatible_build_for_target(old_build, new_build.replace(
    b'return driver_flags', b'driver_flags.append("-changed")\n    return driver_flags'), 'aarch64')

# The finalizer transition may only move the exact post-build tail.  These
# independent small programs exercise scope and control-flow changes.
old_finalizer = b"""
def cmake_arguments(definition):
    return ['--no-default-config']
def execute(owner, argv, work, environment, log):
    return run(argv)
def inspect_inputs(owner, args, prepared):
    for output in (work, stage):
        owner.require(not os.path.lexists(output), 'runtime output already exists: ' + str(output))
def build(owner, args):
    selected = inspect_inputs(owner, args, prepared)
    owner.require(ok, 'unchanged postprocess')
    return record
"""
new_finalizer = b"""
import re
def check_cmake_cache(owner, work, command):
    return None
def check_bootstrap_artifacts(owner, source, work, stage):
    return None
def recover_bootstrap(owner, args):
    return None
def cmake_arguments(definition):
    return ['--no-default-config']
def execute(owner, argv, work, environment, log):
    return run(argv)
def inspect_inputs(owner, args, prepared, *, existing=False):
    for output in (work, stage):
        if existing:
            owner.paths.real_directory(output)
            owner.require(owner.paths.canonical_existing(output) == str(output), 'runtime recovery path must be canonical')
        else:
            owner.require(not os.path.lexists(output), 'runtime output already exists: ' + str(output))
def build(owner, args):
    selected = inspect_inputs(owner, args, prepared)
    return finalize(owner, args, prepared, selected, environment)
def finalize(owner, args, prepared, selected, environment):
    from emberbsd_sdk import llvm_runtime, target_toolchain
    source = Path(owner.paths.canonical_existing(args.source))
    definition, base, work, stage = selected.definition, selected.base, selected.work, selected.stage
    native, compiler, recipe, context = selected.native, selected.compiler, selected.recipe, selected.context
    bootstrap, bootstrap_root = selected.bootstrap, selected.bootstrap_root
    owner.require(ok, 'unchanged postprocess')
    return record
"""
assert runtime.compatible_build_for_target(old_finalizer, new_finalizer, 'aarch64')
for changed in (
    new_finalizer.replace(b'--no-default-config', b'--no-default-config -fshort-wchar'),
    new_finalizer.replace(b'return run(argv)', b'unexpected()\n    return run(argv)'),
    new_finalizer.replace(b"    owner.require(ok, 'unchanged postprocess')",
                          b"    unexpected()\n    owner.require(ok, 'unchanged postprocess')"),
    new_finalizer.replace(b'def recover_bootstrap(owner, args):',
                          b'def recover_bootstrap(owner, args=unexpected()):'),
    new_finalizer.replace(b'if existing:', b'if existing or bypass:'),
):
    assert changed != new_finalizer
    assert not runtime.compatible_build_for_target(old_finalizer, changed, 'aarch64')
dynamic_old = old_finalizer.replace(b'selected = inspect_inputs(owner, args, prepared)',
                                    b"selected = globals()['recover_bootstrap'](owner, args)")
dynamic_new = new_finalizer.replace(b'selected = inspect_inputs(owner, args, prepared)',
                                    b"selected = globals()['recover_bootstrap'](owner, args)")
assert not runtime.compatible_build_for_target(dynamic_old, dynamic_new, 'aarch64')
current_build = (files / 'build.py').read_bytes()
normalized = runtime.normalize_export_revision(current_build)
assert normalized is not None and normalized != current_build
assert runtime.normalize_recipe_recording(normalized) is not None
mutated_export = current_build.replace(b'owner.shared_export_revision()',
                                       b'owner.git_revision(git, owner.PORTS)')
assert mutated_export != current_build
assert runtime.normalize_export_revision(mutated_export) == mutated_export

old_cli = b"""
def main(arguments):
    build = commands.add_parser('build')
    for name in ('sysroot', 'os-source', 'host-prefix', 'target-prefix', 'work', 'stage'):
        build.add_argument('--' + name, required=True)
    build.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
    build.add_argument('--bootstrap-stage')
    build.add_argument('--original-source', help='prepared source used by the bootstrap stage')
    build.add_argument('--jobs', type=int, default=1)
    verify = commands.add_parser('verify')
    for parser in (build, verify):
        parser.add_argument('--target', choices=('aarch64', 'amd64', 'riscv32'), required=True)
        parser.add_argument('--phase', choices=('builtins', 'bootstrap', 'full'), default='full')
    for parser in (prepare, verify_source, build):
        parser.add_argument('--source', required=True)
    for parser in (prepare, verify_source, build, verify):
        parser.add_argument('--git')
    args = cli.parse_args(arguments)
    if args.command == 'build':
        import build as producer
        record = producer.build(owner, args)
"""
new_cli = b"""
def main(arguments):
    build = commands.add_parser('build')
    recover = commands.add_parser('finalize-bootstrap')
    for parser in (build, recover):
        for name in ('sysroot', 'os-source', 'host-prefix', 'target-prefix', 'work', 'stage'):
            parser.add_argument('--' + name, required=True)
        parser.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
        parser.add_argument('--bootstrap-stage')
        parser.add_argument('--original-source', help='prepared source used by the bootstrap stage')
        parser.add_argument('--jobs', type=int, default=1)
    verify = commands.add_parser('verify')
    for parser in (build, recover, verify):
        parser.add_argument('--target', choices=('aarch64', 'amd64', 'riscv32'), required=True)
    for parser in (build, verify):
        parser.add_argument('--phase', choices=('builtins', 'bootstrap', 'full'), default='full')
    recover.add_argument('--phase', choices=('bootstrap',), default='bootstrap')
    for parser in (prepare, verify_source, build, recover):
        parser.add_argument('--source', required=True)
    for parser in (prepare, verify_source, build, recover, verify):
        parser.add_argument('--git')
    args = cli.parse_args(arguments)
    if args.command == 'build':
        import build as producer
        record = producer.build(owner, args)
"""
assert runtime.build_cli(old_cli, 'aarch64') == runtime.build_cli(new_cli, 'aarch64')
assert runtime.RECIPE_COMPAT_API == 1
assert runtime.compatible_runtime_recipe(old_finalizer, new_finalizer, old_cli, new_cli,
                                         'aarch64', 'aarch64')
assert not runtime.compatible_runtime_recipe(
    old_finalizer, new_finalizer.replace(b'--no-default-config', b'--no-default-config -fshort-wchar'),
    old_cli, new_cli, 'aarch64', 'aarch64')
for changed in (
    new_cli.replace(b"default='clang'", b"default='gcc'"),
    new_cli.replace(b"required=True", b"required=False", 1),
    new_cli.replace(b"producer.build(owner, args)", b"producer.other(owner, args)"),
    new_cli.replace(b"default=1", b"default=2", 1),
):
    assert changed != new_cli
    assert runtime.build_cli(old_cli, 'aarch64') != runtime.build_cli(changed, 'aarch64')


prefix = 'pkgsrc/lang/compiler-rt/'
build_name, cli_name, dist_name = (prefix + 'files/build.py', prefix + 'files/runtime.py', prefix + 'distinfo')
patch_name = prefix + 'patches/patch-builtins'
patch_bytes = b'--- a/compiler-rt/lib/builtins/a.c\n+++ b/compiler-rt/lib/builtins/a.c\n@@ -1 +1 @@\n-old\n+new\n'
old_dist = b'BLAKE2s (source.tar.xz) = unchanged\n'
new_dist = old_dist + b'SHA1 (patch-builtins) = ' + hashlib.sha1(patch_bytes).hexdigest().encode() + b'\n'
old_blobs = {build_name: old_finalizer, cli_name: old_cli, dist_name: old_dist}
new_blobs = {build_name: new_finalizer, cli_name: new_cli, dist_name: new_dist, patch_name: patch_bytes}
def recipe(blobs):
    return {'ports_revision': 'a' * 40, 'files': {name: hashlib.sha256(data).hexdigest() for name, data in blobs.items()}}
old_recipe, new_recipe = recipe(old_blobs), recipe(new_blobs)
changed_paths = ['compiler-rt/lib/builtins/a.c']
assert runtime.compatible_builtins_recipe(old_recipe, new_recipe, old_blobs, new_blobs,
                                           changed_paths, 'aarch64', 'aarch64')
mutated_blobs = dict(new_blobs, **{build_name: new_finalizer.replace(
    b'--no-default-config', b'--no-default-config -fshort-wchar')})
assert not runtime.compatible_builtins_recipe(old_recipe, recipe(mutated_blobs), old_blobs, mutated_blobs,
                                               changed_paths, 'aarch64', 'aarch64')
cmake_patch = patch_bytes.replace(b'compiler-rt/lib/builtins/a.c',
                                  b'compiler-rt/lib/builtins/CMakeLists.txt')
cmake_dist = old_dist + b'SHA1 (patch-builtins) = ' + hashlib.sha1(cmake_patch).hexdigest().encode() + b'\n'
cmake_blobs = dict(new_blobs, **{patch_name: cmake_patch, dist_name: cmake_dist})
assert not runtime.compatible_builtins_recipe(old_recipe, recipe(cmake_blobs), old_blobs, cmake_blobs,
                                               ['compiler-rt/lib/builtins/CMakeLists.txt'],
                                               'aarch64', 'aarch64')
bad_hash = copy.deepcopy(new_recipe)
bad_hash['files'][patch_name] = '0' * 64
assert not runtime.compatible_builtins_recipe(old_recipe, bad_hash, old_blobs, new_blobs,
                                               changed_paths, 'aarch64', 'aarch64')
assert not runtime.compatible_builtins_recipe(old_recipe, new_recipe, old_blobs, new_blobs,
                                               changed_paths + ['compiler-rt/lib/builtins/other.c'],
                                               'aarch64', 'aarch64')
duplicate = dict(new_blobs, **{dist_name: new_dist + b'SHA1 (patch-builtins) = ' + b'0' * 40 + b'\n'})
assert not runtime.compatible_builtins_recipe(old_recipe, recipe(duplicate), old_blobs, duplicate,
                                               changed_paths, 'aarch64', 'aarch64')
extra = dict(new_blobs, **{prefix + 'files/unknown.py': b'unexpected'})
assert not runtime.compatible_builtins_recipe(old_recipe, recipe(extra), old_blobs, extra,
                                               changed_paths, 'aarch64', 'aarch64')
bad_dist = dict(new_blobs, **{dist_name: new_dist + b'BLAKE2s (other.tar.xz) = changed\n'})
assert not runtime.compatible_builtins_recipe(old_recipe, recipe(bad_dist), old_blobs, bad_dist,
                                               changed_paths, 'aarch64', 'aarch64')

print('runtime finalizer split and refusals: PASS')

print('runtime phase compatibility and refusals: PASS')
