#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare, build and verify the canonical common LLVM runtime stages."""
import argparse
import ast
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import source as owner


def main(arguments):
    arguments = owner.load_sdk(arguments)
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--pkgsrc-root', help='explicit exported pkgsrc root')
    commands = cli.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--archive', required=True)
    prepare.add_argument('--patch', required=True)
    verify_source = commands.add_parser('verify-source')
    build = commands.add_parser('build')
    for name in ('sysroot', 'os-source', 'host-prefix', 'target-prefix', 'work', 'stage'):
        build.add_argument('--' + name, required=True)
    build.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
    build.add_argument('--bootstrap-stage')
    build.add_argument('--jobs', type=int, default=1)
    wasi_build = commands.add_parser('wasi-builtins')
    for name in ('source', 'host-prefix', 'work', 'stage'):
        wasi_build.add_argument('--' + name, required=True)
    wasi_build.add_argument('--git')
    wasi_build.add_argument('--jobs', type=int, default=1)
    wasi_verify = commands.add_parser('wasi-verify')
    for name in ('source', 'stage'):
        wasi_verify.add_argument('--' + name, required=True)
    wasi_verify.add_argument('--git')
    freestanding_cli(commands)
    verify = commands.add_parser('verify')
    verify.add_argument('--stage', required=True)
    verify.add_argument('--base')
    verify.add_argument('--source', help='currently selected prepared LLVM source')
    verify.add_argument('--original-source', help='prepared source used by the existing runtime')
    for parser in (build, verify):
        parser.add_argument('--target', choices=('aarch64', 'amd64', 'riscv32'), required=True)
        parser.add_argument('--phase', choices=('builtins', 'bootstrap', 'full'), default='full')
    for parser in (prepare, verify_source, build):
        parser.add_argument('--source', required=True)
    for parser in (prepare, verify_source, build, verify):
        parser.add_argument('--git')
    args = cli.parse_args(arguments)
    if args.command in ('build', 'verify') and args.target == 'riscv32' and args.phase == 'full':
        cli.error('riscv32 supports only builtins and bootstrap')
    owner.select_recipe_root(args.pkgsrc_root)
    if args.command == 'prepare':
        record = owner.prepare_source(args.archive, args.source, args.patch, args.git)
    elif args.command == 'verify-source':
        record = owner.verify_source(args.source, args.git)
    elif args.command == 'build':
        import build as producer
        record = producer.build(owner, args)
    elif args.command in ('wasi-builtins', 'wasi-verify'):
        import wasi
        record = wasi.build(owner, args) if args.command == 'wasi-builtins' else wasi.verify(owner, args)
    elif args.command in ('freestanding-builtins', 'freestanding-verify'):
        import freestanding
        record = (freestanding.build(owner, args, args.target) if args.command == 'freestanding-builtins'
                  else freestanding.verify(owner, args, args.target))
    else:
        from emberbsd_sdk import llvm_runtime
        import build as producer
        # A stage is identified by its manifest; an SDK that supports it
        # checks names, links and artifacts without hashing the bytes again.
        content = {'content': False} if getattr(llvm_runtime, 'STAGE_CONTENT_API', 0) >= 1 else {}
        record = llvm_runtime.validate_stage(args.stage, target=args.target,
            required_components=producer.PROFILES[args.phase], base=args.base, **content)
        # Compare the complete owner contract, not just a caller-provided
        # subset of input hashes. Unrelated commits do not change these inputs.
        current, _ = owner.recipe(args.git)
        expected = producer.effective_recipe(owner, current, args.git)
        owner.require(record['llvm_version'] == current['llvm_version'] and
                      record['source'] == {k: current['source'][k] for k in ('archive', 'sha512')},
                      'runtime source selection changed')
        if record['recipe']['files'] != expected['files']:
            compatible_source(owner, record, expected, args.source, args.original_source, args.git)
    print(owner.jsonio.json_bytes(record).decode(), end='')


def freestanding_cli(commands):
    import freestanding
    for name in ('freestanding-builtins', 'freestanding-verify'):
        parser = commands.add_parser(name)
        parser.add_argument('--target', choices=tuple(freestanding.PROFILES), required=True)
        for argument in ('source', 'stage'):
            parser.add_argument('--' + argument, required=True)
        parser.add_argument('--git')
        if name == 'freestanding-builtins':
            for argument in ('host-prefix', 'work'):
                parser.add_argument('--' + argument, required=True)
            parser.add_argument('--jobs', type=int, default=1)


def compatible_build_for_target(previous, current, machine_arch):
    """Compare build code after removing provably false architecture guards."""
    if not isinstance(machine_arch, str) or not machine_arch:
        return False

    def effective(data):
        tree = ast.parse(data)
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'cmake_arguments']
        if (len(functions) != 1 or
                'definition' not in [arg.arg for arg in functions[0].args.posonlyargs + functions[0].args.args]):
            return None
        # The selected definition must remain read-only and cannot escape.
        # Otherwise a preceding statement could change the tested arch.
        parents = {child: parent for parent in ast.walk(functions[0])
                   for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(functions[0]):
            if isinstance(node, ast.Name) and node.id == 'definition':
                parent = parents.get(node)
                if (not isinstance(parent, ast.Subscript) or parent.value is not node or
                        not isinstance(parent.ctx, ast.Load) or not isinstance(parent.slice, ast.Constant) or
                        not isinstance(parent.slice.value, str)):
                    return None
        # Arbitrary dead code can change Python scope or turn this function
        # into a generator, so only an existing list augmentation is safe.
        def false_arch_guard(node, index):
            if not isinstance(node, ast.If) or node.orelse or len(node.body) != 1:
                return False
            operation = node.body[0]
            if not (isinstance(operation, ast.AugAssign) and isinstance(operation.op, ast.Add) and
                    isinstance(operation.target, ast.Name) and operation.target.id == 'driver_flags' and
                    isinstance(operation.value, ast.List) and all(isinstance(v, ast.Constant) and
                    isinstance(v.value, str) for v in operation.value.elts)):
                return False
            if not any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and
                       t.id == 'driver_flags' for t in n.targets) for n in functions[0].body[:index]):
                return False
            test = node.test
            return (isinstance(test, ast.Compare) and len(test.ops) == 1 and
                    isinstance(test.ops[0], ast.Eq) and len(test.comparators) == 1 and
                    isinstance(test.left, ast.Subscript) and isinstance(test.left.value, ast.Name) and
                    test.left.value.id == 'definition' and isinstance(test.left.slice, ast.Constant) and
                    test.left.slice.value == 'arch' and isinstance(test.comparators[0], ast.Constant) and
                    isinstance(test.comparators[0].value, str) and test.comparators[0].value != machine_arch)
        functions[0].body = [n for index, n in enumerate(functions[0].body) if not false_arch_guard(n, index)]
        return ast.dump(tree, include_attributes=False)

    try:
        left, right = effective(previous), effective(current)
        return left is not None and left == right
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return False


def compatible_source(owner, stage, expected, source, original_source, git):
    """Compare prepared payloads when recipe selectors or CLI dispatch changed."""
    owner.require(source is not None and original_source is not None,
                  'runtime recipe inputs changed: select both prepared sources')
    current = owner.verify_source(source, git)
    original_path = Path(owner.paths.canonical_existing(original_source))
    original = owner.jsonio.read_json(original_path / owner.SOURCE_MANIFEST)
    owner.require(isinstance(original, dict) and original.get('format') == 'emberbsd-llvm-source' and
                  original.get('version') in (1, 2), 'invalid original LLVM source record')
    owner.require(all(original.get(k) == current[k] for k in ('llvm_version', 'components', 'source')),
                  'original LLVM source selection changed')
    # Both prepared trees are identified by the digests their preparation
    # recorded; equal digests mean the same patched payload.
    owner.require(original.get('tree_sha256') == current['tree_sha256'],
                  'original LLVM source payload differs')
    old_files = original.get('recipe', {}).get('files')
    owner.require(isinstance(old_files, dict) and all(stage['recipe']['files'].get(k) == v
                  for k, v in old_files.items()), 'runtime original source recipe differs')
    exempt = {'pkgsrc/lang/llvm/version.mk', 'pkgsrc/lang/compiler-rt/files/source.py',
              'pkgsrc/lang/compiler-rt/files/runtime.py'}
    old = {k: v for k, v in stage['recipe']['files'].items() if k not in exempt}
    new = {k: v for k, v in expected['files'].items() if k not in exempt}
    build_name = 'pkgsrc/lang/compiler-rt/files/build.py'
    if old.get(build_name) != new.get(build_name):
        previous_build = owner.process.capture([git, '-C', str(owner.PORTS), 'show',
            stage['recipe']['ports_revision'] + ':' + build_name],
            env=owner.process.sanitized_environment()).stdout
        current_build = (Path(__file__).parent / 'build.py').read_bytes()
        owner.require(owner.digest(previous_build) == old.get(build_name) and
                      owner.digest(current_build) == new.get(build_name),
                      'runtime build or patch inputs changed')
        from emberbsd_sdk import targets
        selected_arch = targets.target_definition(stage.get('target'))['arch']
        owner.require(stage.get('machine_arch') == selected_arch and
                      compatible_build_for_target(previous_build, current_build, selected_arch),
                      'runtime build or patch inputs changed')
        old.pop(build_name)
        new.pop(build_name)
    owner.require(old == new, 'runtime build or patch inputs changed')
    runtime_name = 'pkgsrc/lang/compiler-rt/files/runtime.py'
    previous = owner.process.capture([git, '-C', str(owner.PORTS), 'show',
        stage['recipe']['ports_revision'] + ':' + runtime_name],
        env=owner.process.sanitized_environment()).stdout
    owner.require(owner.digest(previous) == stage['recipe']['files'][runtime_name],
                  'original runtime CLI differs from stage recipe')
    owner.require(build_cli(previous, stage.get('target')) == build_cli(Path(__file__).read_bytes(), stage.get('target')),
                  'runtime build CLI or dispatch changed')


def build_cli(data, target=None):
    """Compare the build parser and dispatch without executing historical code."""
    tree = ast.parse(data)
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    additions = """
cli.add_argument('--pkgsrc-root', help='explicit exported pkgsrc root')
freestanding_cli(commands)
wasi_build = commands.add_parser('wasi-builtins')
for name in ('source', 'host-prefix', 'work', 'stage'):
    wasi_build.add_argument('--' + name, required=True)
wasi_build.add_argument('--git')
wasi_build.add_argument('--jobs', type=int, default=1)
wasi_verify = commands.add_parser('wasi-verify')
for name in ('source', 'stage'):
    wasi_verify.add_argument('--' + name, required=True)
wasi_verify.add_argument('--git')
verify.add_argument('--source', help='currently selected prepared LLVM source')
verify.add_argument('--original-source', help='prepared source used by the existing runtime')
owner.select_recipe_root(args.pkgsrc_root)
if args.command in ('build', 'verify') and args.target == 'riscv32' and args.phase == 'full':
    cli.error('riscv32 supports only builtins and bootstrap')
"""
    ignored = {ast.dump(n, include_attributes=False) for n in ast.parse(additions).body}
    selected = []
    for node in main.body:
        if ast.dump(node, include_attributes=False) in ignored:
            continue
        if isinstance(node, ast.If):
            cursor = node
            while isinstance(cursor, ast.If):
                selected.append(cursor.test)
                if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'build' and isinstance(n.func.value, ast.Name) and n.func.value.id == 'producer' for n in ast.walk(ast.Module(body=cursor.body, type_ignores=[]))):
                    selected.extend(cursor.body)
                    break
                cursor = cursor.orelse[0] if len(cursor.orelse) == 1 else None
            break
        clone = ast.parse(ast.unparse(node)).body[0]
        for call in ast.walk(clone):
            if isinstance(call, ast.Call) and call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == '--git':
                call.keywords = [k for k in call.keywords if k.arg != 'required']
            if (target in ('aarch64', 'amd64') and isinstance(call, ast.Call) and
                    call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == '--target'):
                for keyword in call.keywords:
                    if keyword.arg == 'choices' and isinstance(keyword.value, ast.Tuple):
                        values = keyword.value.elts
                        if [getattr(v, 'value', None) for v in values] == ['aarch64', 'amd64', 'riscv32']:
                            keyword.value.elts = values[:2]
        selected.append(clone)

    return tuple(ast.dump(n, include_attributes=False) for n in selected)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as error:
        print('llvm-runtimes: ' + str(error), file=sys.stderr)
        status = getattr(error, 'returncode', 1)
        sys.exit(status if status >= 0 else 128 - status)
