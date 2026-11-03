#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare, build and verify the canonical common LLVM runtime stages."""
import argparse
import ast
import hashlib
import re
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
    recover = commands.add_parser('finalize-bootstrap')
    for parser in (build, recover):
        for name in ('sysroot', 'os-source', 'host-prefix', 'target-prefix', 'work', 'stage'):
            parser.add_argument('--' + name, required=True)
        parser.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
        parser.add_argument('--bootstrap-stage')
        parser.add_argument('--original-source', help='prepared source used by the bootstrap stage')
        parser.add_argument('--jobs', type=int, default=1)
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
    elif args.command == 'finalize-bootstrap':
        import build as producer
        record = producer.recover_bootstrap(owner, args)
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


def normalize_export_revision(data):
    # Only this metadata-only export identity transition is normalized.
    export = b"""    if owner.EXPORTED:
        export = owner.jsonio.read_json(owner.PKGSRC.parent / 'pkgsrc-export.json')
        owner.require(isinstance(export, dict) and export.get('format') == 'emberbsd-pkgsrc-shared-export'
                      and export.get('version') == 2 and isinstance(export.get('identity'), dict),
                      'invalid shared pkgsrc export identity')
        revision = export['identity'].get('ports_commit')
        owner.require(isinstance(revision, str) and re.fullmatch(r'[0-9a-f]{40}', revision) is not None,
                      'invalid shared pkgsrc export revision')
    else:
        revision = owner.git_revision(git, owner.PORTS)
"""
    replacement = b"    revision = None if owner.EXPORTED else owner.git_revision(git, owner.PORTS)\n"
    if export not in data:
        return data
    if data.count(export) != 1:
        return None
    return data.replace(export, replacement, 1)


def normalize_finalizer_refactor(tree):
    """Inline only the reviewed finalizer split and fresh-build input branch."""
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    if 'finalize' not in funcs:
        return True
    required = {'finalize', 'check_cmake_cache', 'check_bootstrap_artifacts',
                'recover_bootstrap', 'inspect_inputs', 'build'}
    if not required <= funcs.keys() or any(
            sum(isinstance(n, ast.FunctionDef) and n.name == name for n in tree.body) != 1
            for name in required):
        return False

    def plain(function, names):
        args = function.args
        all_args = args.posonlyargs + args.args + args.kwonlyargs
        return (not function.decorator_list and function.returns is None and
                not getattr(function, 'type_params', []) and
                not args.posonlyargs and [a.arg for a in args.args] == names and
                not args.kwonlyargs and not args.defaults and not args.kw_defaults and
                args.vararg is None and args.kwarg is None and
                all(a.annotation is None and a.type_comment is None for a in all_args))

    signatures = {'finalize': ['owner', 'args', 'prepared', 'selected', 'environment'],
                  'check_cmake_cache': ['owner', 'work', 'command'],
                  'check_bootstrap_artifacts': ['owner', 'source', 'work', 'stage'],
                  'recover_bootstrap': ['owner', 'args']}
    if any(not plain(funcs[name], names) for name, names in signatures.items()):
        return False
    prefix = ast.parse("""from emberbsd_sdk import llvm_runtime, target_toolchain
source = Path(owner.paths.canonical_existing(args.source))
definition, base, work, stage = selected.definition, selected.base, selected.work, selected.stage
native, compiler, recipe, context = selected.native, selected.compiler, selected.recipe, selected.context
bootstrap, bootstrap_root = selected.bootstrap, selected.bootstrap_root
""").body
    finish = funcs['finalize']
    dump = lambda node: ast.dump(node, include_attributes=False)
    if [dump(n) for n in finish.body[:5]] != [dump(n) for n in prefix]:
        return False
    build = funcs['build']
    expected_return = ast.parse('return finalize(owner, args, prepared, selected, environment)').body[0]
    if not build.body or dump(build.body[-1]) != dump(expected_return):
        return False
    build.body[-1:] = finish.body[5:]

    inputs = funcs['inspect_inputs']
    args = inputs.args
    if (len(args.kwonlyargs) != 1 or args.kwonlyargs[0].arg != 'existing' or
            args.kwonlyargs[0].annotation is not None or len(args.kw_defaults) != 1 or
            not isinstance(args.kw_defaults[0], ast.Constant) or args.kw_defaults[0].value is not False):
        return False
    branch = ast.parse("""if existing:
    owner.paths.real_directory(output)
    owner.require(owner.paths.canonical_existing(output) == str(output), 'runtime recovery path must be canonical')
else:
    owner.require(not os.path.lexists(output), 'runtime output already exists: ' + str(output))
""").body[0]
    matches = []
    for node in ast.walk(inputs):
        if isinstance(node, ast.For):
            for index, child in enumerate(node.body):
                if dump(child) == dump(branch):
                    matches.append((node, index))
    if len(matches) != 1:
        return False
    node, index = matches[0]
    node.body[index:index + 1] = branch.orelse
    args.kwonlyargs = []
    args.kw_defaults = []
    if any(isinstance(n, ast.Name) and n.id == 'existing' for n in ast.walk(inputs)):
        return False
    removed = {'finalize', 'check_cmake_cache', 'check_bootstrap_artifacts', 'recover_bootstrap'}
    tree.body = [n for n in tree.body if not isinstance(n, ast.FunctionDef) or n.name not in removed]
    dynamic = {'globals', 'locals', 'vars', 'eval', 'exec', 'getattr', '__import__'}
    if any((isinstance(n, ast.Name) and n.id in removed | dynamic) or
           (isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in removed)
           for n in ast.walk(tree)):
        return False
    # The new import serves only the normalized export metadata check.
    if any(isinstance(n, ast.Name) and n.id == 're' for n in ast.walk(tree)):
        return False
    imports = [n for n in tree.body if isinstance(n, ast.Import) and
               len(n.names) == 1 and n.names[0].name == 're' and n.names[0].asname is None]
    if len(imports) != 1:
        return False
    tree.body.remove(imports[0])
    return True


def compatible_build_for_target(previous, current, machine_arch, atomic_defaults=False):
    """Compare build inputs after reviewed target-guard and metadata normalization."""
    if not isinstance(machine_arch, str) or not machine_arch:
        return False

    previous = normalize_export_revision(previous)
    current = normalize_export_revision(current)
    if previous is None or current is None:
        return False
    previous = normalize_recipe_recording(previous)
    current = normalize_recipe_recording(current)
    if previous is None or current is None:
        return False

    def effective(data):
        tree = ast.parse(data)
        if not normalize_finalizer_refactor(tree):
            return None
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'cmake_arguments']
        if (len(functions) != 1 or
                'definition' not in [arg.arg for arg in functions[0].args.posonlyargs + functions[0].args.args]):
            return None
        # Normalize only the reviewed bootstrap preflight replacement.
        old_check = ast.parse("""owner.require(bootstrap['source'] == {k: prepared['source'][k] for k in ('archive', 'sha512')} and bootstrap['recipe']['files'] == recipe['files'], 'bootstrap runtime source or recipe inputs differ')""").body[0]
        replacement = ast.parse("""from runtime import require_bootstrap_inputs
require_bootstrap_inputs(owner, bootstrap, recipe, prepared, args)""").body
        replacement_keys = [ast.dump(n, include_attributes=False) for n in replacement]
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'inspect_inputs':
                for branch in ast.walk(node):
                    if not isinstance(branch, ast.If):
                        continue
                    keys = [ast.dump(n, include_attributes=False) for n in branch.body]
                    for pos in range(len(keys) - 1):
                        if keys[pos:pos + 2] == replacement_keys:
                            branch.body[pos:pos + 2] = [old_check]
                            break
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
        # into a generator, so only known flag/settings updates are safe.
        def false_arch_guard(node, prior):
            if not isinstance(node, ast.If) or node.orelse or len(node.body) != 1:
                return False
            operation = node.body[0]
            atomic_default_update = False
            if (isinstance(operation, ast.AugAssign) and isinstance(operation.op, ast.Add) and
                    isinstance(operation.target, ast.Name) and operation.target.id == 'driver_flags' and
                    isinstance(operation.value, ast.List) and all(isinstance(v, ast.Constant) and
                    isinstance(v.value, str) for v in operation.value.elts)):
                if not any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and
                           t.id == 'driver_flags' for t in n.targets) for n in prior):
                    return False
            elif (isinstance(operation, ast.Expr) and isinstance(operation.value, ast.Call) and
                  isinstance(operation.value.func, ast.Attribute) and
                  isinstance(operation.value.func.value, ast.Name) and
                  operation.value.func.value.id == 'settings' and operation.value.func.attr == 'update' and
                  not operation.value.args and bool(operation.value.keywords) and
                  all(k.arg is not None and isinstance(k.value, ast.Constant) and
                      isinstance(k.value.value, str) for k in operation.value.keywords)):
                if not any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and
                           t.id == 'settings' for t in n.targets) for n in prior):
                    return False
                values = {item.arg: item.value.value for item in operation.value.keywords}
                atomic_default_update = (atomic_defaults and values == {
                    'COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN': 'ON',
                    'COMPILER_RT_BUILD_STANDALONE_LIBATOMIC': 'OFF'})
            else:
                return False
            test = node.test
            arch_guard = (isinstance(test, ast.Compare) and len(test.ops) == 1 and
                    isinstance(test.ops[0], ast.Eq) and len(test.comparators) == 1 and
                    isinstance(test.left, ast.Subscript) and isinstance(test.left.value, ast.Name) and
                    test.left.value.id == 'definition' and isinstance(test.left.slice, ast.Constant) and
                    test.left.slice.value == 'arch' and isinstance(test.comparators[0], ast.Constant) and
                    isinstance(test.comparators[0].value, str))
            if not arch_guard:
                return False
            selected_arch = test.comparators[0].value
            return selected_arch != machine_arch or (
                atomic_default_update and machine_arch == 'riscv32' and selected_arch == machine_arch)
        body = functions[0].body
        for node in list(ast.walk(functions[0])):
            if not isinstance(node, ast.If):
                continue
            ancestor = parents.get(node)
            while ancestor is not functions[0] and isinstance(ancestor, ast.If):
                ancestor = parents.get(ancestor)
            if ancestor is not functions[0]:
                continue
            root = node
            while parents.get(root) is not functions[0]:
                root = parents[root]
            index = body.index(root)
            if not false_arch_guard(node, body[:index]):
                continue
            parent = parents[node]
            for field in ('body', 'orelse'):
                children = getattr(parent, field, None)
                if isinstance(children, list) and node in children:
                    children.remove(node)
                    break
        return ast.dump(tree, include_attributes=False)

    try:
        left, right = effective(previous), effective(current)
        return left is not None and left == right
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return False


def normalize_recipe_recording(data):
    """Normalize the package-relative input names in one reviewed transition."""
    old_path = (b"        files[str(path.relative_to(owner.PORTS))] = "
                b"owner.inventory.sha256_file(path)\n")
    new_path = (b"        files[owner.input_name(path)] = "
                b"owner.inventory.sha256_file(path)\n")
    old_revision = (b"    return dict(ports_revision=owner.git_revision(git, owner.PORTS), "
                    b"files=files)\n")
    new_revision = (b"    revision = None if owner.EXPORTED else owner.git_revision(git, owner.PORTS)\n"
                    b"    return dict(ports_revision=revision, files=files)\n")
    if (data.count(old_path) == 1 and data.count(old_revision) == 1 and
            new_path not in data and new_revision not in data):
        return data
    if (data.count(new_path) == 1 and data.count(new_revision) == 1 and
            old_path not in data and old_revision not in data):
        return data.replace(new_path, old_path).replace(new_revision, old_revision)
    if not any(marker in data for marker in (old_path, new_path, old_revision, new_revision)):
        return data
    return None


def atomic_builtin_cmake_defaults(source):
    """Read the upstream defaults that make atomic.c absent from builtins."""
    path = Path(source) / 'compiler-rt/lib/builtins/CMakeLists.txt'
    try:
        data = path.read_bytes()
    except OSError:
        return None
    result = {}
    for name in ('COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN',
                 'COMPILER_RT_BUILD_STANDALONE_LIBATOMIC'):
        pattern = rb'option\(\s*' + name.encode() + rb'\s+"[^"\n]*"\s+(ON|OFF|On|Off)\s*\)'
        matches = re.findall(pattern, data)
        if len(matches) != 1:
            return None
        result[name] = matches[0].decode().upper()
    return result


def atomic_builtin_excluded(stage, original_source, current_source):
    """Prove an RV32 builtins stage omitted atomic.c and standalone libatomic."""
    if (stage.get('machine_arch') != 'riscv32' or 'builtins' not in stage.get('components', ()) or
            not set(stage.get('components', ())) <= {'builtins', 'libunwind-static'}):
        return False
    original = atomic_builtin_cmake_defaults(original_source)
    current = atomic_builtin_cmake_defaults(current_source)
    expected = {'COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN': 'ON',
                'COMPILER_RT_BUILD_STANDALONE_LIBATOMIC': 'OFF'}
    return original == expected and current == expected


def patch_paths(data):
    """Return safe relative paths named by unified patch headers, or None."""
    headers = re.findall(rb'^(---|\+\+\+) ([^\t\n ]+)', data, re.M)
    if not headers or len(headers) % 2:
        return None
    paths = set()
    for index in range(0, len(headers), 2):
        before, after = headers[index:index + 2]
        if before[0] != b'---' or after[0] != b'+++':
            return None
        if before[1] == after[1] == b'/dev/null':
            return None
        pair_paths = []
        for (_, path), prefix in ((before, b'a'), (after, b'b')):
            if path == b'/dev/null':
                pair_paths.append(None)
                continue
            parts = path.split(b'/')
            if (len(parts) < 2 or parts[0] != prefix or
                    any(p in (b'', b'.', b'..') for p in parts) or
                    any(c < 32 or c == 127 or c == 92 for c in path)):
                return None
            pair_paths.append(b'/'.join(parts[1:]))
        if pair_paths[0] is not None and pair_paths[1] is not None and pair_paths[0] != pair_paths[1]:
            return None
        paths.update(path for path in pair_paths if path is not None)
    return paths


def libcxx_only_patch(data):
    """Accept unified patch headers only inside libcxx/include after -p1."""
    paths = patch_paths(data)
    return bool(paths) and all(path.startswith(b'libcxx/include/') and
                               len(path.split(b'/')) >= 3 for path in paths)


def atomic_builtin_only_patch(data):
    """Recognize a patch confined to the compiler-rt atomic builtin source."""
    return patch_paths(data) == {b'compiler-rt/lib/builtins/atomic.c'}


def require_bootstrap_inputs(owner, bootstrap, recipe, prepared, args):
    owner.require(bootstrap['source'] == {k: prepared['source'][k] for k in ('archive', 'sha512')},
                  'bootstrap runtime source or recipe inputs differ')
    if bootstrap['recipe']['files'] != recipe['files']:
        compatible_source(owner, bootstrap, recipe, args.source, args.original_source, args.git)


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
    same_tree = original.get('tree_sha256') == current['tree_sha256']
    old_files = original.get('recipe', {}).get('files')
    owner.require(isinstance(old_files, dict) and all(stage['recipe']['files'].get(k) == v
                  for k, v in old_files.items()), 'runtime original source recipe differs')
    exempt = ({'pkgsrc/lang/llvm/version.mk',
               'pkgsrc/lang/compiler-rt/files/runtime.py'} | owner.NON_OUTPUT_INPUTS)
    old = {k: v for k, v in stage['recipe']['files'].items() if k not in exempt}
    new = {k: v for k, v in expected['files'].items() if k not in exempt}
    if not same_tree:
        patch_prefix = 'pkgsrc/lang/compiler-rt/patches/'
        patch_names = {k for k in set(old) | set(new) if k.startswith(patch_prefix) and old.get(k) != new.get(k)}
        owner.require(patch_names, 'runtime source patch delta missing')
        bootstrap_components = {'builtins', 'libunwind-static'}
        for name in patch_names:
            for files, historic in ((old, True), (new, False)):
                if name not in files:
                    continue
                if historic:
                    data = owner.process.capture([git, '-C', str(owner.PORTS), 'show',
                        stage['recipe']['ports_revision'] + ':' + name],
                        env=owner.process.sanitized_environment()).stdout
                else:
                    data = owner.read(owner.OWNER / 'patches' / Path(name).name)
                owner.require(owner.digest(data) == files[name], 'runtime source patch identity differs')
                if libcxx_only_patch(data):
                    owner.require(bool(stage.get('components')) and
                                  set(stage['components']) <= bootstrap_components,
                                  'libc++ source patch affects selected runtime inputs')
                elif atomic_builtin_only_patch(data):
                    # AArch64 has always excluded this source. RV32 may reuse
                    # a recorded bootstrap only when both source versions
                    # exclude atomic.c and do not build standalone libatomic.
                    owner.require(stage.get('machine_arch') == 'aarch64' or
                                  atomic_builtin_excluded(stage, original_path, source),
                                  'atomic builtin source patch affects selected runtime inputs')
                else:
                    owner.require(False, 'runtime source patch affects selected runtime inputs')
            old.pop(name, None)
            new.pop(name, None)
        # Permit only checksum entries for the reviewed changed patches.
        distinfo = 'pkgsrc/lang/compiler-rt/distinfo'
        owner.require(distinfo in old and distinfo in new, 'runtime distinfo missing')
        previous = owner.process.capture([git, '-C', str(owner.PORTS), 'show',
            stage['recipe']['ports_revision'] + ':' + distinfo],
            env=owner.process.sanitized_environment()).stdout
        current_distinfo = owner.read(owner.OWNER / 'distinfo')
        owner.require(owner.digest(previous) == old[distinfo] and
                      owner.digest(current_distinfo) == new[distinfo],
                      'runtime distinfo identity differs')
        changed = {Path(name).name.encode() for name in patch_names}
        def unaffected(data):
            return b''.join(line for line in data.splitlines(keepends=True)
                if not any(line.startswith(b'SHA1 (' + name + b') = ') for name in changed))
        owner.require(unaffected(previous) == unaffected(current_distinfo),
                      'runtime archive or unrelated patch checksum differs')
        old.pop(distinfo)
        new.pop(distinfo)
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
        atomic_defaults = atomic_builtin_excluded(stage, original_path, source)
        owner.require(stage.get('machine_arch') == selected_arch and
                      compatible_build_for_target(previous_build, current_build, selected_arch,
                                                  atomic_defaults=atomic_defaults),
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


def normalize_recover_parser(main):
    """Reduce the reviewed recovery parser refactor to the original build CLI."""
    dump = lambda node: ast.dump(node, include_attributes=False)
    nodes = main.body
    recover = ast.parse("recover = commands.add_parser('finalize-bootstrap')").body[0]
    phase = ast.parse("recover.add_argument('--phase', choices=('bootstrap',), default='bootstrap')").body[0]
    marker = [n for n in nodes if dump(n) == dump(recover)]
    if not marker:
        return True
    if len(marker) != 1 or sum(dump(n) == dump(phase) for n in nodes) != 1:
        return False
    new_setup = ast.parse("""for parser in (build, recover):
    for name in ('sysroot', 'os-source', 'host-prefix', 'target-prefix', 'work', 'stage'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
    parser.add_argument('--bootstrap-stage')
    parser.add_argument('--original-source', help='prepared source used by the bootstrap stage')
    parser.add_argument('--jobs', type=int, default=1)
""").body[0]
    old_setup = ast.parse("""for name in ('sysroot', 'os-source', 'host-prefix', 'target-prefix', 'work', 'stage'):
    build.add_argument('--' + name, required=True)
build.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
build.add_argument('--bootstrap-stage')
build.add_argument('--original-source', help='prepared source used by the bootstrap stage')
build.add_argument('--jobs', type=int, default=1)
""").body
    target_loop = ast.parse("""for parser in (build, verify):
    parser.add_argument('--target', choices=('aarch64', 'amd64', 'riscv32'), required=True)
""").body[0]
    target_loop_old = ast.parse("""for parser in (build, verify):
    parser.add_argument('--target', choices=('aarch64', 'amd64'), required=True)
""").body[0]
    phase_loop = ast.parse("""for parser in (build, verify):
    parser.add_argument('--phase', choices=('builtins', 'bootstrap', 'full'), default='full')
""").body[0]
    allowed = {('build', 'recover', 'verify'),
               ('prepare', 'verify_source', 'build', 'recover'),
               ('prepare', 'verify_source', 'build', 'recover', 'verify')}
    out = []
    setup_count = 0
    for node in nodes:
        if dump(node) in (dump(recover), dump(phase)):
            continue
        if dump(node) == dump(new_setup):
            out.extend(old_setup)
            setup_count += 1
            continue
        if (isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple) and
                all(isinstance(n, ast.Name) for n in node.iter.elts)):
            names = tuple(n.id for n in node.iter.elts)
            if 'recover' in names:
                if names not in allowed:
                    return False
                node.iter.elts = [n for n in node.iter.elts if n.id != 'recover']
        out.append(node)
    if setup_count != 1:
        return False
    pairs = [i for i in range(len(out) - 1)
             if dump(out[i]) in (dump(target_loop), dump(target_loop_old)) and
             dump(out[i + 1]) == dump(phase_loop)]
    if len(pairs) != 1:
        return False
    i = pairs[0]
    out[i].body.extend(out[i + 1].body)
    del out[i + 1]
    main.body = out
    return True


RECIPE_COMPAT_API = 1


def compatible_runtime_recipe(previous_build, current_build, previous_cli, current_cli, target, machine_arch):
    """Compare the ordinary producer build and dispatch for one target."""
    return (compatible_build_for_target(previous_build, current_build, machine_arch) and
            build_cli(previous_cli, target) == build_cli(current_cli, target))


def builtins_recipe_blob_names(previous, current):
    """Return validated Git blob names for a scoped builtins recipe update."""
    try:
        if (set(previous) != {'ports_revision', 'files'} or set(current) != {'ports_revision', 'files'} or
                any(not isinstance(item['ports_revision'], str) or
                    re.fullmatch(r'[0-9a-f]{40}', item['ports_revision']) is None
                    for item in (previous, current))):
            return None
        old, new = previous['files'], current['files']
        if not isinstance(old, dict) or not isinstance(new, dict):
            return None
        if any(not isinstance(name, str) or not isinstance(value, str) or
               re.fullmatch(r'[0-9a-f]{64}', value) is None
               for files in (old, new) for name, value in files.items()):
            return None
        prefix = 'pkgsrc/lang/compiler-rt/'
        required = {prefix + 'files/build.py', prefix + 'files/runtime.py', prefix + 'distinfo'}
        if not required <= old.keys() or not required <= new.keys():
            return None
        changed = {name for name in old.keys() | new.keys() if old.get(name) != new.get(name)}
        patches = {name for name in changed if name.startswith(prefix + 'patches/patch-')}
        if (not patches or changed - patches - required or
                any(re.fullmatch(re.escape(prefix + 'patches/patch-') + r'[A-Za-z0-9_.+-]+', name) is None
                    for name in patches)):
            return None
        return sorted(changed | required)
    except (KeyError, TypeError):
        return None


def compatible_builtins_recipe(previous, current, previous_blobs, current_blobs,
                               changed_paths, target, machine_arch):
    """Check a selected builtins source update without executing old code."""
    try:
        names = builtins_recipe_blob_names(previous, current)
        if names is None or not isinstance(previous_blobs, dict) or not isinstance(current_blobs, dict):
            return False
        old, new = previous['files'], current['files']
        prefix = 'pkgsrc/lang/compiler-rt/'
        build, cli, distinfo = (prefix + 'files/build.py', prefix + 'files/runtime.py',
                                prefix + 'distinfo')
        patches = {name for name in names if name.startswith(prefix + 'patches/patch-')}
        needed = set(names)
        for recorded, blobs in ((old, previous_blobs), (new, current_blobs)):
            if set(blobs) != needed & recorded.keys():
                return False
            for name, data in blobs.items():
                if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != recorded[name]:
                    return False
        if not compatible_runtime_recipe(previous_blobs[build], current_blobs[build],
                                         previous_blobs[cli], current_blobs[cli],
                                         target, machine_arch):
            return False
        expected = set(changed_paths)
        darwin = 'compiler-rt/cmake/Modules/AddCompilerRT.cmake'
        if not expected or any(not isinstance(name, str) or
                not (name == darwin or
                     (name.startswith('compiler-rt/lib/builtins/') and
                      Path(name).suffix in ('.c', '.h', '.inc')))
                for name in expected):
            return False
        touched = set()
        for name in patches:
            for blobs in (previous_blobs, current_blobs):
                if name not in blobs:
                    continue
                data = blobs[name]
                line = b'SHA1 (' + Path(name).name.encode() + b') = ' + hashlib.sha1(data).hexdigest().encode()
                if blobs[distinfo].splitlines().count(line) != 1:
                    return False
                oldpaths = [line[6:].decode('utf-8') for line in data.splitlines()
                            if line.startswith(b'--- a/')]
                newpaths = [line[6:].decode('utf-8') for line in data.splitlines()
                            if line.startswith(b'+++ b/')]
                if not oldpaths or oldpaths != newpaths:
                    return False
                touched.update(newpaths)
        if touched != expected:
            return False
        patch_names = {Path(name).name.encode() for name in patches}
        for blobs in (previous_blobs, current_blobs):
            for name in patches:
                marker = b'SHA1 (' + Path(name).name.encode() + b') = '
                entries = [line for line in blobs[distinfo].splitlines() if line.startswith(marker)]
                if name not in blobs:
                    if entries:
                        return False
                elif entries != [marker + hashlib.sha1(blobs[name]).hexdigest().encode()]:
                    return False
        def unchanged_distinfo(data):
            return b''.join(line for line in data.splitlines(keepends=True)
                            if not any(line.startswith(b'SHA1 (' + name + b') = ')
                                       for name in patch_names))
        return unchanged_distinfo(previous_blobs[distinfo]) == unchanged_distinfo(current_blobs[distinfo])
    except (KeyError, TypeError, UnicodeError, SyntaxError, ValueError):
        return False


def build_cli(data, target=None):
    """Compare the build parser and dispatch without executing historical code."""
    tree = ast.parse(data)
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    if not normalize_recover_parser(main):
        return ('unsupported-recovery-parser', ast.dump(main, include_attributes=False))
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
build.add_argument('--original-source', help='prepared source used by the bootstrap stage')
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
