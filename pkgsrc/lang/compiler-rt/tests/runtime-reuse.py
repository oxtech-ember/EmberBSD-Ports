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
print('runtime phase compatibility and refusals: PASS')
