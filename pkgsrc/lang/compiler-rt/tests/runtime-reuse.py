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
             'pkgsrc/lang/llvm/version.mk': 'old', 'patch': 'same'}
expected = {'files': dict(old_files, **{'pkgsrc/lang/compiler-rt/files/source.py': 'new',
    'pkgsrc/lang/llvm/version.mk': 'new', 'pkgsrc/lang/compiler-rt/files/runtime.py': 'new',
    'pkgsrc/lang/compiler-rt/files/build.py': 'same'})}
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

print('runtime source reuse, target guards and CLI: PASS')
