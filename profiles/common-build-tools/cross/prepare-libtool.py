#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Build the shared pkgsrc cross-libtool recipe into one OS TOOLDIR context."""
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

from llvm_host import load_sdk


def recipe_digest(exported):
    """Fingerprint the effective shared libtool recipe and complete patch inputs."""
    root = Path(exported).resolve(strict=True)
    entries = []
    for name in ('cross/cross-libtool-base', 'devel/libtool-base', 'devel/libtool'):
        package = root / name
        if not package.is_dir() or package.is_symlink():
            raise ValueError('missing libtool recipe directory')
        for item in sorted(package.rglob('*')):
            relative = item.relative_to(package)
            if not (relative.parts[0] in ('files', 'patches') or
                    (len(relative.parts) == 1 and
                     (item.name.startswith('Makefile') or item.name == 'distinfo' or item.suffix == '.mk'))):
                continue
            if item.is_dir() and not item.is_symlink():
                continue
            resolved = item.resolve(strict=True)
            if not resolved.is_file() or not resolved.is_relative_to(root):
                raise ValueError('invalid libtool recipe input')
            entries.append((str(item.relative_to(root)), os.readlink(item) if item.is_symlink() else None,
                            hashlib.sha256(resolved.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(entries, separators=(',', ':')).encode()).hexdigest()


def verify_pkgsrc_tree(exported, ports, git, patcher, process, env):
    """Check the selected graph export's pin and current cross-libtool rule patch."""
    exported = Path(exported)
    revision_file = exported / 'EMBERBSD-PKGSRC-REVISION'
    pinned = process.capture([git, '-C', str(ports), 'rev-parse', 'HEAD:upstream/pkgsrc'],
                             env=env).stdout.decode('ascii').strip() + '\n'
    if (revision_file.is_symlink() or not revision_file.is_file() or
            revision_file.read_text(encoding='ascii') != pinned):
        raise ValueError('pkgsrc tree does not match the pinned upstream revision')
    patch = Path(ports) / 'profiles/common-build-tools/patches/cross-libtool-tool-paths.patch'
    process.capture([patcher, '--batch', '--fuzz=0', '-R', '--dry-run', '-p1', '-i', str(patch)],
                    cwd=str(exported), env=env)
    return exported


def context_name(identity):
    data = json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()
    return 'context-' + hashlib.sha256(data).hexdigest()


def context_root(root):
    """Create or check the owned directory of all cross-libtool contexts."""
    root = Path(root)
    owner = root / '.cross-libtool-owner'
    if os.path.lexists(root):
        if root.is_symlink() or not root.is_dir() or owner.is_symlink():
            raise ValueError('incompatible cross-libtool context root')
        try:
            if owner.read_text() != 'cross-libtool-context-v1\n':
                raise ValueError('incompatible cross-libtool context root')
        except OSError as exc:
            raise ValueError('incompatible cross-libtool context root') from exc
    else:
        root.mkdir()
        owner.write_text('cross-libtool-context-v1\n')
    return root


SYSROOT_ALIAS = 'sysroot'


def bind_sysroot(root, sysroot):
    """Point the stable sysroot alias of the context root at the selected stage.

    Contexts, their compiler bindings and the configured libtool name only
    this alias, so renaming or replacing the stage does not change a context
    key. The caller holds the OS TOOLDIR for the whole run, and the alias is
    repointed before any context is selected or used, so a reused context
    always reaches the stage selected by this run. The headers and libraries
    it was configured with stay in the key through sysroot_inputs.
    """
    root = context_root(root)
    alias = root / SYSROOT_ALIAS
    if os.path.lexists(alias) and not alias.is_symlink():
        raise ValueError('incompatible cross-libtool sysroot alias')
    if not os.path.isabs(sysroot) or os.path.realpath(sysroot) != sysroot:
        raise ValueError('select the real sysroot directory for the cross-libtool alias')
    fd, temp = tempfile.mkstemp(prefix='.sysroot-', dir=root)
    os.close(fd)
    os.unlink(temp)
    os.symlink(sysroot, temp)
    os.replace(temp, alias)
    if os.path.realpath(alias) != sysroot:
        raise ValueError('cross-libtool sysroot alias does not reach the selected sysroot')
    return str(alias)


def claim_context(root, identity):
    """Reuse a matching complete context or recreate only its own partial output."""
    root = context_root(root)
    context = root / context_name(identity)
    if os.path.lexists(context):
        config = context / 'configure-inputs.json'
        try:
            if context.is_symlink() or not context.is_dir() or config.is_symlink():
                raise ValueError('incompatible cross-libtool context')
            with config.open(encoding='utf-8') as stream:
                old = json.load(stream)
            if old != identity:
                raise ValueError('incompatible cross-libtool context')
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError('incompatible cross-libtool context') from exc
        if (context / 'bin/target-libtool').exists():
            return context, True
        current = root / 'current'
        if current.is_symlink() and os.readlink(current) == context.name:
            raise ValueError('cannot replace an incomplete active cross-libtool context')
        # Delete only outputs belonging to a matching interrupted producer.
        for child in context.iterdir():
            if child.name not in ('configure-inputs.json', 'depends.log', 'build.log', 'target-tools', 'pkgdb', 'bin') and not re.fullmatch(r'cross-NetBSD-[0-9.]+-[A-Za-z0-9_]+', child.name):
                raise ValueError('incompatible files in partial cross-libtool context')
        shutil.rmtree(context)
    context.mkdir()
    with (context / 'configure-inputs.json').open('x', encoding='utf-8') as stream:
        json.dump(identity, stream, sort_keys=True)
        stream.write('\n')
    return context, False


def reported_target_tools(context):
    """Return the tools directory target.mk records for this context.

    The cross profile compares TOOLDIR with _EMBER_TARGET_TOOLS as strings,
    the same way CROSS_DESTDIR must equal _EMBER_TARGET_SYSROOT. The current
    alias reaches this directory but is a different spelling.
    """
    tools = Path(context) / 'target-tools'
    record = tools / 'target.mk'
    if tools.is_symlink() or record.is_symlink() or not record.is_file():
        raise ValueError('prepared target tools record is missing')
    recorded = None
    prefix = '_EMBER_TARGET_TOOLS:= '
    for line in record.read_text(encoding='utf-8').splitlines():
        if not line.startswith(prefix):
            continue
        if recorded is not None:
            raise ValueError('prepared target tools record is ambiguous')
        recorded = line[len(prefix):]
    if recorded != str(tools):
        raise ValueError('prepared target tools differ from the selected context')
    return recorded


def cross_libtool_result(alias, context, package):
    """Report the stable libtool alias and the tools path the guard accepts."""
    return {'libtool': str(alias), 'target_tools': reported_target_tools(context), 'package': package}


def activate_context(tooldir, root, context):
    """Switch the stable aliases only after a complete context is verified."""
    tooldir, root, context = Path(tooldir), Path(root), Path(context)
    tool = context / 'bin/target-libtool'
    if context.parent != root or not tool.is_file():
        raise ValueError('installed cross-libtool is missing')
    target_tools = context / 'target-tools'
    target_alias = target_tools / 'bin/target-libtool'
    target_expected = os.path.relpath(tool, target_alias.parent)
    if os.path.lexists(target_alias):
        if not target_alias.is_symlink() or os.readlink(target_alias) != target_expected:
            raise ValueError('incompatible target-tools libtool alias')
    else:
        if not (target_alias.parent.is_dir() and not target_alias.parent.is_symlink()):
            raise ValueError('selected target-tools directory is missing')
        target_alias.symlink_to(target_expected)
    current = root / 'current'
    alias = tooldir / 'bin/target-libtool'
    expected = os.path.relpath(root / 'current/bin/target-libtool', alias.parent)
    if os.path.lexists(alias) and (not alias.is_symlink() or os.readlink(alias) != expected):
        raise ValueError('incompatible target-libtool alias')
    if os.path.lexists(current):
        if (not current.is_symlink() or not re.fullmatch(r'context-[0-9a-f]{64}', os.readlink(current))):
            raise ValueError('incompatible active cross-libtool context')
    fd, temp = tempfile.mkstemp(prefix='.current-', dir=root)
    os.close(fd)
    os.unlink(temp)
    os.symlink(context.name, temp)
    os.replace(temp, current)
    if not os.path.lexists(alias):
        alias.symlink_to(expected)
    return alias


def sysroot_inputs(sysroot, inventory):
    """Record the headers and libraries used by the configured compiler."""
    return {name: inventory.snapshot_installed_tree(os.path.join(sysroot, name))
            for name in ('lib', 'usr/include', 'usr/lib')}


def clang_runtime(sysroot, target, stage, base, paths, llvm_runtime, application_toolchain):
    if stage:
        return llvm_runtime.validate_stage(stage, target=target,
            required_components=llvm_runtime.FULL_COMPONENTS,
            base=paths.canonical_existing(base or sysroot))
    return application_toolchain.load_clang_runtime(sysroot, target=target)


def clang_c_foundation(sysroot, target, result, base, paths, application_toolchain):
    if not result:
        return None
    if getattr(application_toolchain, 'FOUNDATION_TOOLCHAIN_API', 0) < 1:
        raise ValueError('the selected SDK cannot select a C-foundation runtime')
    options = {}
    if base:
        if getattr(application_toolchain, 'FOUNDATION_RUNTIME_BASE_API', 0) < 1:
            raise ValueError('the selected SDK cannot bind a separate C-foundation runtime base')
        options['runtime_base'] = paths.canonical_existing(base)
    return application_toolchain.load_clang_c_foundation_runtime(
        result, sysroot, target=target, **options)


def _package_database_path(database):
    """Accept one real absolute database directory."""
    if isinstance(database, bytes):
        database = database.decode('utf-8')
    database = database.strip()
    if (not os.path.isabs(database) or any(c.isspace() or c in '\\"\'`$#;:' for c in database)
            or not os.path.isdir(database)
            or os.path.realpath(database) != os.path.normpath(database)):
        raise ValueError('native pkg_install reports an invalid package database')
    return os.path.normpath(database)


def native_package_database(pkg_admin, process, env):
    """Return the package database of the selected native pkg_install."""
    # Each native prefix configures its own database; do not assume var/db/pkg.
    # config-var reads the binary's compiled configuration, which is not relocated
    # when the prefix moves. Callers with a selected MAKECONF use that instead.
    output = process.capture([pkg_admin, 'config-var', 'PKG_DBDIR'], env=env).stdout
    return _package_database_path(output)


def _installed_prefixes(contents):
    """Return every @cwd path with only the line ending removed."""
    found = []
    with open(contents, 'r', encoding='utf-8') as stream:
        for line in stream:
            if not line.startswith('@cwd '):
                continue
            path = line[len('@cwd '):]
            if path.endswith('\n'):
                path = path[:-1]
            if path.endswith('\r'):
                path = path[:-1]
            found.append(path)
    return found


def selected_host_database(database, prefix, sysroot):
    """Prove an explicit database is the selected host prefix, not the target."""
    database = _package_database_path(database)
    prefix = os.path.normpath(prefix)
    sysroot = os.path.normpath(sysroot)
    if os.path.commonpath((database, sysroot)) == sysroot:
        raise ValueError('native package database is inside the target sysroot')
    found = False
    with os.scandir(database) as entries:
        for entry in entries:
            if entry.is_symlink():
                raise ValueError('native package database contains a symlink')
            if not entry.is_dir(follow_symlinks=False):
                continue
            contents = os.path.join(entry.path, '+CONTENTS')
            if os.path.islink(contents) or not os.path.isfile(contents):
                raise ValueError('native package database entry has no package contents')
            installed = _installed_prefixes(contents)
            if not installed or any(os.path.normpath(path) != prefix for path in installed):
                raise ValueError('native package database belongs to another prefix')
            found = True
    if not found:
        raise ValueError('native package database contains no packages')
    return database


# pkgsrc tools.<OPSYS>.mk runs system sed and echo while bmake reads it.
# The host prefix has gsed, not sed. The SDK show-vars PATH is the prefix
# tool directories only; these system directories follow that prefix.
_SYSTEM_COMMAND_PATH = ('/usr/bin', '/bin', '/usr/sbin', '/sbin')


def show_vars_environment(env, prefix):
    """Return the native MAKECONF query environment.

    Prefix bin and sbin come first. The system command directories follow so
    bmake can run sed and echo. Ambient package-database variables are removed.
    """
    query_env = dict(env)
    query_env.pop('PKG_DBDIR', None)
    query_env.pop('HOST_PKG_DBDIR', None)
    query_env['PATH'] = os.pathsep.join((prefix + '/bin', prefix + '/sbin', *_SYSTEM_COMMAND_PATH))
    return query_env


def native_build_path(prefix):
    """Return the PATH used for depends, the package build, and their queries."""
    return os.pathsep.join((prefix + '/bin', prefix + '/gnu/bin', prefix + '/sbin',
                            *_SYSTEM_COMMAND_PATH))


def resolve_native_database(*, pkg_admin, process, env, prefix, sysroot,
                            native_makeconf=None, make=None, pkgsrc=None):
    """Select the host database from MAKECONF, or from pkg_admin when omitted."""
    if native_makeconf is None:
        return native_package_database(pkg_admin, process, env)
    if not make or not pkgsrc:
        raise ValueError('explicit native database requires the selected pkgsrc tree')
    # Ignore an ambient PKG_DBDIR. The selected file is the authority.
    query_env = show_vars_environment(env, prefix)
    output = process.capture([
        make, '-C', os.path.join(pkgsrc, 'pkgtools/pkg_install'),
        'USE_CROSS_COMPILE=no', 'MAKECONF=' + native_makeconf,
        'show-vars', 'VARNAMES=PREFIX PKG_DBDIR'], env=query_env).stdout
    text = output.decode('utf-8').splitlines()
    if len(text) != 2 or any(not line or line != line.strip() for line in text):
        raise ValueError('selected MAKECONF returned invalid installation destinations')
    if os.path.normpath(text[0]) != os.path.normpath(prefix):
        raise ValueError('selected MAKECONF prefix differs from the host prefix')
    return selected_host_database(text[1], prefix, sysroot)


def package_database_conf(pkgdb):
    """Register native dependencies in the selected prefix database."""
    return ['HOST_PKG_DBDIR=' + pkgdb, 'PKG_DBDIR=' + pkgdb]


def build_package(make, prefix, pkgdb, context, pkg_add, process, env):
    """Install dependencies in the native prefix before staging this tool."""
    process.run_logged([*make, 'PREFIX=' + prefix,
                        'PKG_ADD=' + pkg_add + ' -K ' + pkgdb + ' -U', 'depends'],
                       str(context / 'depends.log'), env=env)
    # The selected cross compiler supplies the target sysroot and ABI. Do not
    # carry host CFLAGS (for example a Darwin SDK path) into the generated
    # target libtool's LTCFLAGS; target system headers are compiler defaults.
    process.run_logged([*make, 'PREFIX=' + str(context), 'CFLAGS=-O2', 'package'],
                       str(context / 'build.log'), env=env)


def build_selected_package(make, prefix, pkgdb, sysroot, context, pkg_add, process, env, *,
                           prove_contents):
    """Install dependencies only after the locked database still has this prefix.

    The caller holds the host-prefix lock and the lock for this same database
    path. Those SDK context locks exclude other producers that take them in
    the same lock directory. They do not stop pkg_add that never takes them.
    For an explicit native MAKECONF, the installed-prefix scan is the
    precondition for depends and uses the database path just selected.
    """
    if prove_contents:
        confirmed = selected_host_database(pkgdb, prefix, sysroot)
        if confirmed != os.path.normpath(pkgdb):
            raise ValueError('selected package database changed')
        pkgdb = confirmed
    build_package(make, prefix, pkgdb, context, pkg_add, process, env)


def main():
    sdk, argv = load_sdk()
    from emberbsd_sdk import (application_toolchain, inventory, llvm_runtime, native_toolset,
                              paths, process, target_toolchain)
    from emberbsd_sdk.errors import SDKError
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host-prefix', 'compiler', 'os-tools', 'sysroot', 'output',
                 'work-parent', 'git'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--distdir')
    parser.add_argument('--lock-directory', help='shared prefix/pkgdb lock directory')
    parser.add_argument('--native-makeconf',
                        help='selected native MAKECONF; its host PKG_DBDIR replaces pkg_admin config-var')
    parser.add_argument('--pkgsrc-export',
                        help='read-only stage from scripts/pkgsrc-export-stage.py prepare')
    parser.add_argument('--pkgsrc-tree',
                        help='read-only pkgsrc export already used by the package graph')
    parser.add_argument('--runtime-stage')
    parser.add_argument('--runtime-base')
    parser.add_argument('--c-foundation-result')
    parser.add_argument('--c-foundation-base')
    parser.add_argument('--target', choices=('aarch64', 'amd64', 'riscv32'), required=True)
    parser.add_argument('--compiler-family', choices=('clang', 'gcc'), default='clang')
    parser.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
    parser.add_argument('--jobs', type=int, default=1)
    a = parser.parse_args(argv)
    if a.jobs < 1:
        raise SDKError('jobs must be positive')
    if a.compiler_family != 'clang' and a.runtime_stage:
        raise SDKError('--runtime-stage requires Clang')
    if a.runtime_base and not a.runtime_stage:
        raise SDKError('--runtime-base requires --runtime-stage')
    if a.compiler_family != 'clang' and a.c_foundation_result:
        raise SDKError('--c-foundation-result requires Clang')
    if a.c_foundation_base and not a.c_foundation_result:
        raise SDKError('--c-foundation-base requires --c-foundation-result')
    if a.c_foundation_result and (a.runtime_stage or a.runtime_base):
        raise SDKError('--c-foundation-result cannot be combined with --runtime-stage or --runtime-base')
    if a.pkgsrc_export and a.pkgsrc_tree:
        raise SDKError('select only one of --pkgsrc-export or --pkgsrc-tree')
    if a.target == 'riscv32' and not a.c_foundation_result:
        raise SDKError('riscv32 cross-libtool requires --c-foundation-result')
    for value in (sdk, a.host_prefix, a.compiler, a.os_tools, a.sysroot,
                  a.output, a.work_parent, a.git, a.distdir, a.runtime_stage, a.runtime_base,
                  a.c_foundation_result, a.c_foundation_base, a.lock_directory, a.pkgsrc_tree,
                  a.pkgsrc_export, a.native_makeconf):
        if value is None:
            continue
        if not os.path.isabs(value) or any(c.isspace() or c in '\\"\'`$#;:' for c in value):
            raise SDKError('select absolute cross-tool paths without make metacharacters')
    prefix = paths.canonical_existing(a.host_prefix)
    lock_directory = paths.canonical_existing(a.lock_directory or os.path.dirname(prefix))
    with contextlib.ExitStack() as locks:
        # Select the tools and their database under the prefix lock.
        locks.enter_context(process.ContextLocks([prefix], lock_directory))
        native = native_toolset.load_host_prefix(a.host_prefix,
            required_roles={'python', 'make', 'pkg_add', 'pkg_admin', 'gpatch', 'sh', 'cc', 'cxx'},
            compiler_family=a.host_compiler_family)
        query_env = process.sanitized_environment()
        query_env['PATH'] = os.pathsep.join((prefix + '/bin', prefix + '/sbin'))
        stage_sysroot = paths.canonical_existing(a.sysroot)
        if a.native_makeconf and not (a.pkgsrc_tree or a.pkgsrc_export):
            raise SDKError('explicit native database requires --pkgsrc-tree or --pkgsrc-export')
        # The compiled answer does not need the pkgsrc tree. An explicit MAKECONF
        # is resolved only after that tree has been verified below.
        pkgdb = None
        if not a.native_makeconf:
            pkgdb = resolve_native_database(
                pkg_admin=native.tool('pkg_admin'), process=process, env=query_env,
                prefix=prefix, sysroot=stage_sysroot)
            locks.enter_context(process.ContextLocks([pkgdb], lock_directory))
        tooldir = paths.canonical_existing(a.os_tools)
        output = os.path.join(paths.canonical_existing(os.path.dirname(a.output)), os.path.basename(a.output))
        if os.path.commonpath((output, tooldir)) != tooldir or output == tooldir:
            raise SDKError('cross-libtool output must be inside the selected OS TOOLDIR')
        if os.path.lexists(output):
            owner = Path(output) / '.cross-libtool-owner'
            if (os.path.islink(output) or not os.path.isdir(output) or owner.is_symlink()
                    or not owner.is_file() or owner.read_text() != 'cross-libtool-context-v1\n'):
                raise SDKError('incompatible cross-libtool output')
        work = paths.canonical_existing(a.work_parent)
        distdir = paths.canonical_existing(a.distdir) if a.distdir else None
        compiler = paths.canonical_existing(a.compiler)
        git = paths.canonical_existing(a.git)
        ports = Path(__file__).resolve().parents[3]
        cross = ports / 'profiles/common-build-tools/cross'
        env = process.sanitized_environment()
        env['PATH'] = native_build_path(prefix)
        env['TMPDIR'] = work
        python = native.tool('python')
        direct_export = None
        verified_export = None
        if a.pkgsrc_tree:
            direct_export = verify_pkgsrc_tree(paths.canonical_existing(a.pkgsrc_tree),
                                               ports, git, native.tool('gpatch'), process, env)
        elif a.native_makeconf:
            spec = importlib.util.spec_from_file_location(
                'emberbsd_pkgsrc_source_identity', ports / 'scripts/pkgsrc-source-identity.py')
            identity = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(identity)
            try:
                verified_export = identity.shared_export(paths.canonical_existing(a.pkgsrc_export), ports,
                                                         git, sdk, native.tool('gpatch'))
            except ValueError as error:
                raise SDKError(str(error)) from error
        if a.native_makeconf:
            database_tree = direct_export if direct_export is not None else verified_export
            pkgdb = resolve_native_database(
                pkg_admin=native.tool('pkg_admin'), process=process, env=query_env,
                prefix=prefix, sysroot=stage_sysroot,
                native_makeconf=paths.canonical_existing(a.native_makeconf),
                make=native.tool('make'), pkgsrc=str(database_tree))
            # Same prefix-parent lock as the compiled database. Do not retarget it.
            locks.enter_context(process.ContextLocks([pkgdb], lock_directory))
        try:
            sysroot = bind_sysroot(output, stage_sysroot)
        except (OSError, ValueError) as error:
            raise SDKError(str(error)) from error
        with tempfile.TemporaryDirectory(prefix='.cross-libtool-', dir=work) as temporary:
            tmp = Path(temporary)
            native_conf = tmp / 'native.mk'
            if a.pkgsrc_tree:
                exported = direct_export
            elif a.pkgsrc_export:
                # A stage keyed by the Git fingerprint of the export inputs.
                # It is verified against the current inputs and only read.
                # --native-makeconf already resolved this to the inner pkgsrc tree.
                if verified_export is not None:
                    exported = verified_export
                else:
                    spec = importlib.util.spec_from_file_location(
                        'emberbsd_pkgsrc_source_identity', ports / 'scripts/pkgsrc-source-identity.py')
                    identity = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(identity)
                    try:
                        exported = identity.shared_export(paths.canonical_existing(a.pkgsrc_export), ports,
                                                          git, sdk, native.tool('gpatch'))
                    except ValueError as error:
                        raise SDKError(str(error)) from error
            else:
                exported = tmp / 'pkgsrc'
                command = [python, '-B', str(ports / 'scripts/prepare-pkgsrc.py'), str(exported),
                           '--git', git, '--patch', native.tool('gpatch')]
                process.capture(command, env=env)
            command = [python, '-B', str(cross / 'prepare-tools.py'), '--sdk-source', sdk,
                       '--target', a.target, '--compiler-family', a.compiler_family,
                       '--host-compiler-family', a.host_compiler_family, '--host-prefix', prefix,
                       '--sysroot', sysroot]
            if a.c_foundation_result:
                command += ['--c-foundation-result', paths.canonical_existing(a.c_foundation_result)]
                if a.c_foundation_base:
                    command += ['--c-foundation-base', paths.canonical_existing(a.c_foundation_base)]
            elif a.runtime_stage:
                command += ['--runtime-stage', paths.canonical_existing(a.runtime_stage)]
                if a.runtime_base:
                    command += ['--runtime-base', paths.canonical_existing(a.runtime_base)]
            # The SDK validates the actual foundation and runtime before any reuse.
            triplet = {'aarch64': 'aarch64--netbsd', 'amd64': 'x86_64--netbsd',
                       'riscv32': 'riscv32--netbsd'}[a.target]
            if a.compiler_family == 'clang':
                compiler_record = target_toolchain.clang_compiler(compiler, triplet, host=native.host, env=env)
                if a.c_foundation_result:
                    runtime_record = clang_c_foundation(stage_sysroot, a.target,
                        paths.canonical_existing(a.c_foundation_result), a.c_foundation_base,
                        paths, application_toolchain)
                else:
                    runtime_record = clang_runtime(stage_sysroot, a.target, a.runtime_stage, a.runtime_base,
                                                   paths, llvm_runtime, application_toolchain)
            else:
                # GCC's selected foundation lacks an LLVM manifest; its ABI inputs
                # are the installed headers and libraries used by configure.
                compiler_record = {'prefix': compiler}
                runtime_record = {name: inventory.snapshot_tree(os.path.join(stage_sysroot, name))
                                  for name in ('usr/include', 'usr/lib')}
            runtime_record = copy.deepcopy(runtime_record)
            if isinstance(runtime_record.get('recipe'), dict):
                runtime_record['recipe'].pop('ports_revision', None)
            if isinstance(runtime_record.get('base'), dict):
                runtime_record['base'].pop('os_revision', None)
            probe = tmp / 'probe-tools'
            process.capture([*command, compiler, tooldir, str(probe)], env=env)
            binding = probe / 'commands/commands.json'
            compiler_record['bound_tools'] = {
                item.name: {'path': str(item.resolve()), 'sha256': inventory.sha256_file(str(item.resolve()))}
                for item in (probe / 'bin').iterdir()
                if item.is_symlink() and not item.resolve().is_relative_to(probe)}
            selected_tools = {role: inventory.sha256_file(os.path.realpath(value))
                              for role, value in native.tools.items()}
            # Bound commands import this SDK module at execution time. Other
            # producer sources are reflected in the effective recipe and bindings.
            bindings_code = inventory.sha256_file(os.path.join(sdk, 'src/emberbsd_sdk/compiler_bindings.py'))
            identity = {'version': 1, 'target': a.target, 'compiler_family': a.compiler_family,
                        'target_cflags': '-O2',
                        'host': native.as_dict(), 'native_tool_hashes': selected_tools,
                        'compiler': compiler_record, 'sysroot': sysroot, 'runtime': runtime_record,
                        'sysroot_inputs': sysroot_inputs(stage_sysroot, inventory),
                        'wrapper_binding': json.loads(binding.read_text()) if binding.exists() else None,
                        'recipe': recipe_digest(exported),
                        'cross_config': {name: inventory.sha256_file(str(exported / name)) for name in
                                         ('EMBERBSD-CROSS-MK.CONF', 'EMBERBSD-DEFAULTS-MK.CONF',
                                          'EMBERBSD-NATIVE-TOOLS.MK')},
                        'cross_pkgsrc_rules': {name: inventory.sha256_file(str(exported / name)) for name in
                                               ('mk/cwrappers.mk', 'mk/buildlink3/bsd.buildlink3.mk')},
                        'binding_code': bindings_code, 'object_format': 'ELF', 'package_cross_mode': 'native'}
            context, reused = claim_context(output, identity)
            target_tools = context / 'target-tools'
            if not reused:
                process.capture([*command, compiler, tooldir, str(target_tools)], env=env)
            process.capture([python, '-B', str(cross / 'prepare-native-tools.py'), '--sdk-source', sdk,
                             'write', '--host-prefix', prefix, '--compiler-family', a.host_compiler_family,
                             '--output', str(native_conf)], env=env)
            conf = tmp / 'cross.conf'
            chosen_distdir = distdir or str(tmp / 'distfiles')
            conf.write_text('\n'.join([
                'LOCALBASE=' + prefix, 'TOOLBASE=' + prefix,
                *package_database_conf(pkgdb), 'UNPRIVILEGED=yes',
                'PKG_TOOLS_BIN=' + prefix + '/sbin', 'NATIVE_PKG_TOOLS_BIN=' + prefix + '/sbin',
                '.if defined(BSD_PKG_MK)', 'EMBERBSD_SDK_SOURCE=' + sdk,
                'EMBERBSD_HOST_PREFIX=' + prefix, 'EMBERBSD_NATIVE_TOOLSET_MAKECONF=' + str(native_conf),
                'EMBERBSD_CROSS_TOOLS=' + str(target_tools), 'EMBERBSD_CROSS_SYSROOT=' + sysroot,
                'EMBERBSD_CROSS_HOST_PREFIX=' + prefix, 'EMBERBSD_CROSS_TARGET=' + a.target,
                'EMBERBSD_CROSS_COMPILER_FAMILY=' + a.compiler_family,
                'EMBERBSD_HOST_COMPILER_FAMILY=' + a.host_compiler_family,
                # Keep a shared export unchanged: no work links in package dirs.
                'WRKOBJDIR=' + str(tmp / 'obj'), 'CREATE_WRKDIR_SYMLINK=no', 'DISTDIR=' + chosen_distdir,
                'PACKAGES=' + str(tmp / 'packages'), 'MAKE_JOBS=' + str(a.jobs),
                '.include "' + str(exported / 'EMBERBSD-CROSS-MK.CONF') + '"', '.endif', '']))
            arch = {'aarch64': 'aarch64', 'amd64': 'x86_64', 'riscv32': 'riscv32'}[a.target]
            recipe = str(exported / 'cross/cross-libtool-base')
            query = [native.tool('make'), '-C', recipe, 'MAKECONF=' + str(conf),
                     '-V', '${CROSS_OS_VERSION}', '-V', '${CROSS_OPSYS_VERSION}']
            versions = process.capture(query, env=env).stdout.decode('utf-8').splitlines()
            if (len(versions) != 2 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)+', versions[0]) or
                    not re.fullmatch(r'[0-9]+', versions[1])):
                raise SDKError('cross profile returned invalid target OS version')
            os_version, opsys_version = versions
            make = [native.tool('make'), '-C', recipe, 'MAKECONF=' + str(conf),
                    'USE_CROSS_COMPILE=no', 'TARGET_MACHINE_ARCH=' + arch,
                    'TARGET_OPSYS=NetBSD', 'TARGET_OS_VERSION=' + os_version,
                    'TARGET_OPSYS_VERSION=' + opsys_version, 'TARGET_OBJECT_FMT=ELF',
                    'TARGET_LOWER_OPSYS=netbsd']
            name = process.capture([*make, 'PREFIX=' + str(context), '-V', '${PKGNAME}'], env=env).stdout.decode('utf-8').strip()
            if not name.startswith('cross-libtool-base-') or '/' in name or not name:
                raise SDKError('cross-libtool recipe returned an invalid package name')
            database = context / 'pkgdb'
            if not reused:
                # Prefix and database locks are already held. Re-read @cwd
                # before depends; do not switch to another database.
                build_selected_package(make, prefix, pkgdb, stage_sysroot, context,
                                       native.tool('pkg_add'), process, env,
                                       prove_contents=a.native_makeconf is not None)
                package = tmp / 'packages/All' / (name + '.tgz')
                if not package.is_file():
                    raise SDKError('cross-libtool package was not produced')
                database.mkdir()
                process.capture([native.tool('pkg_add'), '-K', str(database), '-p', str(context), str(package)], env=env)
            process.capture([native.tool('pkg_admin'), '-K', str(database), 'check', name], env=env)
            tool = context / ('cross-NetBSD-' + os_version + '-' + arch) / 'bin/libtool'
            if not tool.is_file() or not os.access(tool, os.X_OK):
                raise SDKError('installed cross-libtool is missing')
            with tool.open('rb') as stream:
                first_line = stream.readline(4096).decode('utf-8').strip()
            if not first_line.startswith('#!') or os.path.realpath(first_line[2:].strip()) != os.path.realpath(native.tool('sh')):
                raise SDKError('cross-libtool interpreter differs from the selected host shell')
            config_env = dict(env, PATH=str(target_tools / 'bin') + os.pathsep + env['PATH'])
            config = process.capture([str(tool), '--config'], env=config_env).stdout.decode('utf-8')
            triplet = {'aarch64': 'aarch64--netbsd', 'amd64': 'x86_64--netbsd',
                       'riscv32': 'riscv32--netbsd'}[a.target]
            if ('host=' + triplet) not in config.splitlines() or str(target_tools / 'bin') not in config:
                raise SDKError('cross-libtool configuration differs from the selected target tools')
            aliases = context / 'bin'
            aliases.mkdir(exist_ok=True)
            alias = aliases / 'target-libtool'
            if not reused:
                alias.symlink_to(os.path.relpath(tool, aliases))
            if alias.resolve(strict=True) != tool.resolve(strict=True):
                raise SDKError('cross-libtool alias resolves outside its installed tool')
            alias = activate_context(tooldir, output, context)
            result = cross_libtool_result(alias, context, name)
            print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        main()
    except Exception as error:
        exit_error(error, 'cross-libtool producer: ')
