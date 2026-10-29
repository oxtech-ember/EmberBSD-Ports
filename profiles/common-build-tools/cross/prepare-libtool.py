#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Build the shared pkgsrc cross-libtool recipe into one OS TOOLDIR context."""
import argparse
import copy
import hashlib
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


def context_name(identity):
    data = json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()
    return 'context-' + hashlib.sha256(data).hexdigest()


def claim_context(root, identity):
    """Reuse a matching complete context or recreate only its own partial output."""
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
            if child.name not in ('configure-inputs.json', 'build.log', 'target-tools', 'pkgdb', 'bin') and not re.fullmatch(r'cross-NetBSD-[0-9.]+-[A-Za-z0-9_]+', child.name):
                raise ValueError('incompatible files in partial cross-libtool context')
        shutil.rmtree(context)
    context.mkdir()
    with (context / 'configure-inputs.json').open('x', encoding='utf-8') as stream:
        json.dump(identity, stream, sort_keys=True)
        stream.write('\n')
    return context, False


def activate_context(tooldir, root, context):
    """Switch the stable aliases only after a complete context is verified."""
    tooldir, root, context = Path(tooldir), Path(root), Path(context)
    tool = context / 'bin/target-libtool'
    if context.parent != root or not tool.is_file():
        raise ValueError('installed cross-libtool is missing')
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
    parser.add_argument('--runtime-stage')
    parser.add_argument('--target', choices=('aarch64', 'amd64'), required=True)
    parser.add_argument('--compiler-family', choices=('clang', 'gcc'), default='clang')
    parser.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
    parser.add_argument('--jobs', type=int, default=1)
    a = parser.parse_args(argv)
    if a.jobs < 1:
        raise SDKError('jobs must be positive')
    if a.compiler_family != 'clang' and a.runtime_stage:
        raise SDKError('--runtime-stage requires Clang')
    for value in (sdk, a.host_prefix, a.compiler, a.os_tools, a.sysroot,
                  a.output, a.work_parent, a.git, a.distdir, a.runtime_stage, a.lock_directory):
        if value is None:
            continue
        if not os.path.isabs(value) or any(c.isspace() or c in '\\"\'`$#;:' for c in value):
            raise SDKError('select absolute cross-tool paths without make metacharacters')
    prefix = paths.canonical_existing(a.host_prefix)
    lock_directory = paths.canonical_existing(a.lock_directory or os.path.dirname(prefix))
    pkgdb = os.path.join(prefix, 'var/db/pkg')
    with process.ContextLocks([prefix, pkgdb], lock_directory):
        native = native_toolset.load_host_prefix(a.host_prefix,
            required_roles={'python', 'make', 'pkg_add', 'pkg_admin', 'gpatch', 'sh', 'cc', 'cxx'},
            compiler_family=a.host_compiler_family)
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
        sysroot = paths.canonical_existing(a.sysroot)
        compiler = paths.canonical_existing(a.compiler)
        git = paths.canonical_existing(a.git)
        ports = Path(__file__).resolve().parents[3]
        cross = ports / 'profiles/common-build-tools/cross'
        env = process.sanitized_environment()
        env['PATH'] = os.pathsep.join((prefix + '/bin', prefix + '/gnu/bin', prefix + '/sbin'))
        env['TMPDIR'] = work
        python = native.tool('python')
        with tempfile.TemporaryDirectory(prefix='.cross-libtool-', dir=work) as temporary:
            tmp = Path(temporary)
            exported = tmp / 'pkgsrc'
            native_conf = tmp / 'native.mk'
            command = [python, '-B', str(ports / 'scripts/prepare-pkgsrc.py'), str(exported),
                       '--git', git, '--patch', native.tool('gpatch')]
            process.capture(command, env=env)
            command = [python, '-B', str(cross / 'prepare-tools.py'), '--sdk-source', sdk,
                       '--target', a.target, '--compiler-family', a.compiler_family,
                       '--host-compiler-family', a.host_compiler_family, '--host-prefix', prefix,
                       '--sysroot', sysroot]
            if a.runtime_stage:
                command += ['--runtime-stage', paths.canonical_existing(a.runtime_stage)]
            # The SDK validates the actual foundation and runtime before any reuse.
            triplet = {'aarch64': 'aarch64--netbsd', 'amd64': 'x86_64--netbsd'}[a.target]
            if a.compiler_family == 'clang':
                compiler_record = target_toolchain.clang_compiler(compiler, triplet, host=native.host, env=env)
                if a.runtime_stage:
                    runtime_record = llvm_runtime.validate_stage(a.runtime_stage, target=a.target,
                        required_components=llvm_runtime.FULL_COMPONENTS, base=sysroot)
                else:
                    runtime_record = application_toolchain.load_clang_runtime(sysroot, target=a.target)
                    for name, digest in runtime_record['base']['files'].items():
                        value = paths.canonical_existing(os.path.join(sysroot, name))
                        if not paths.inside(value, sysroot) or inventory.sha256_file(value) != digest:
                            raise SDKError('LLVM runtime base inputs changed: ' + name)
                    for name, target in runtime_record['base']['symlinks'].items():
                        value = os.path.join(sysroot, name)
                        if not os.path.islink(value) or os.readlink(value) != target or not paths.inside(paths.canonical_existing(value), sysroot):
                            raise SDKError('LLVM runtime base inputs changed: ' + name)
            else:
                # GCC's selected foundation lacks an LLVM manifest; its ABI inputs
                # are the installed headers and libraries used by configure.
                compiler_record = {'prefix': compiler}
                runtime_record = {name: inventory.snapshot_tree(os.path.join(sysroot, name))
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
                        'host': native.as_dict(), 'native_tool_hashes': selected_tools,
                        'compiler': compiler_record, 'sysroot': sysroot, 'runtime': runtime_record,
                        'wrapper_binding': json.loads(binding.read_text()) if binding.exists() else None,
                        'recipe': recipe_digest(exported),
                        'cross_config': {name: inventory.sha256_file(str(exported / name)) for name in
                                         ('EMBERBSD-CROSS-MK.CONF', 'EMBERBSD-DEFAULTS-MK.CONF',
                                          'EMBERBSD-NATIVE-TOOLS.MK')},
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
                'HOST_PKG_DBDIR=' + prefix + '/var/db/pkg',
                'PKG_TOOLS_BIN=' + prefix + '/sbin', 'NATIVE_PKG_TOOLS_BIN=' + prefix + '/sbin',
                '.if defined(BSD_PKG_MK)', 'EMBERBSD_SDK_SOURCE=' + sdk,
                'EMBERBSD_HOST_PREFIX=' + prefix, 'EMBERBSD_NATIVE_TOOLSET_MAKECONF=' + str(native_conf),
                'EMBERBSD_CROSS_TOOLS=' + str(target_tools), 'EMBERBSD_CROSS_SYSROOT=' + sysroot,
                'EMBERBSD_CROSS_HOST_PREFIX=' + prefix, 'EMBERBSD_CROSS_TARGET=' + a.target,
                'EMBERBSD_CROSS_COMPILER_FAMILY=' + a.compiler_family,
                'EMBERBSD_HOST_COMPILER_FAMILY=' + a.host_compiler_family,
                'WRKOBJDIR=' + str(tmp / 'obj'), 'DISTDIR=' + chosen_distdir,
                'PACKAGES=' + str(tmp / 'packages'), 'MAKE_JOBS=' + str(a.jobs),
                '.include "' + str(exported / 'EMBERBSD-CROSS-MK.CONF') + '"', '.endif', '']))
            arch = {'aarch64': 'aarch64', 'amd64': 'x86_64'}[a.target]
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
                    'TARGET_LOWER_OPSYS=netbsd', 'PREFIX=' + str(context)]
            name = process.capture([*make, '-V', '${PKGNAME}'], env=env).stdout.decode('utf-8').strip()
            if not name.startswith('cross-libtool-base-') or '/' in name or not name:
                raise SDKError('cross-libtool recipe returned an invalid package name')
            database = context / 'pkgdb'
            if not reused:
                process.run_logged([*make, 'package'], str(context / 'build.log'), env=env)
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
            triplet = {'aarch64': 'aarch64--netbsd', 'amd64': 'x86_64--netbsd'}[a.target]
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
            result = {'libtool': str(alias), 'target_tools': str(Path(output) / 'current/target-tools'), 'package': name}
            print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        main()
    except Exception as error:
        exit_error(error, 'cross-libtool producer: ')
