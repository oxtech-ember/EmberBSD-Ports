#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted native metadata adapter.
"""Export a bounded pkgsrc dependency closure through native bmake metadata."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

VARIABLES = (
    'PKGNAME', 'PKGVERSION', 'MACHINE_GNU_PLATFORM', 'MACHINE_ARCH', 'USE_CROSS_COMPILE',
    'BOOTSTRAP_DEPENDS', 'TOOL_DEPENDS', 'BUILD_DEPENDS', 'DEPENDS',
    'TEST_DEPENDS', 'INDIRECT_BUILD_DEPENDS', 'INDIRECT_DEPENDS',
    'CROSSTARGETSETTINGS', 'PKGSRC_MAKE_ENV', '_PATH_ORIG',
    '.MAKE.MAKEFILES', 'PATCHDIR', 'FILESDIR', 'DISTINFO_FILE', 'PLIST_SRC',
    'PKG_SKIP_REASON', 'PKG_FAIL_REASON', 'PKG_OPTIONS', 'DISTFILES', 'LOCALPATCHES',
    'CONFIGURE_ARGS', 'CONFIGURE_ENV', 'MAKE_ENV', 'CFLAGS', 'CXXFLAGS',
    'CPPFLAGS', 'LDFLAGS',
)
DEPENDENCIES = {
    'BOOTSTRAP_DEPENDS': 'tool', 'TOOL_DEPENDS': 'tool',
    'BUILD_DEPENDS': 'build', 'DEPENDS': 'runtime', 'TEST_DEPENDS': 'test',
    'INDIRECT_BUILD_DEPENDS': 'build', 'INDIRECT_DEPENDS': 'runtime',
}
RESERVED_MAKE_VARIABLES = {
    'MAKECONF', 'USE_CROSS_COMPILE', 'MAKEFLAGS', 'MFLAGS', '.MAKEFLAGS',
    'MAKEFILE', 'MAKEOBJDIR', 'MAKEOBJDIRPREFIX', 'PKGNAME_REQD', '_MAKEVARS_MK',
}


class ExportError(ValueError):
    """The selected metadata cannot form an unambiguous graph."""


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def assignments(value):
    result = {}
    for word in shlex.split(value):
        key, sep, item = word.partition('=')
        if not sep or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
            raise ExportError('unsupported native recursive assignment')
        if key in result and result[key] != item:
            raise ExportError('conflicting native recursive assignment: ' + key)
        result[key] = item
    return result


def make_variables(values, option='--make-variable'):
    """Parse repeatable, scalar bmake assignments (never make arguments)."""
    result = {}
    for value in values:
        key, sep, item = value.partition('=')
        if (not sep or not (re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) or
                     re.fullmatch(r'PKG_OPTIONS\.[A-Za-z0-9][A-Za-z0-9_.-]*', key)) or
                key in RESERVED_MAKE_VARIABLES or key.startswith('TARGET_') or
                not item or not re.fullmatch(r'[A-Za-z0-9_./:+,@%+-]+', item)):
            raise ExportError('unsupported ' + option + ' assignment')
        if key in result:
            raise ExportError('duplicate ' + option + ': ' + key)
        result[key] = item
    return dict(sorted(result.items()))


def native_current_pattern(base, name):
    """Match cross-bulk native_current: PKGBASE-[0-9]* becomes PKGBASE>=suffix."""
    prefix = base + '-'
    if name.startswith(prefix) and len(name) > len(prefix) and name[len(prefix)].isdigit():
        return base + '>=' + name[len(prefix):]
    return base


def absolute_directory(value, label):
    if not value.startswith('/') or any(character.isspace() for character in value):
        raise ExportError(label + ' is not absolute')
    path = Path(value)
    if not path.is_dir():
        raise ExportError(label + ' is not a directory')
    return path.resolve()


def host_pkg_info_argv(command, host_db, target_db):
    """Require the frozen PKG_INFO to be an absolute executable and the host database."""
    try:
        words = shlex.split(command)
    except ValueError as error:
        raise ExportError('invalid PKG_INFO command') from error
    executable = Path(words[0]) if words else Path()
    if (not words or not words[0].startswith('/') or not executable.is_file()
            or not os.access(executable, os.X_OK)):
        raise ExportError('PKG_INFO executable is not an absolute executable')
    if words.count('-K') != 1:
        raise ExportError('PKG_INFO must select one host package database')
    index = words.index('-K')
    if index + 1 >= len(words):
        raise ExportError('PKG_INFO database is not absolute')
    selected = absolute_directory(words[index + 1], 'PKG_INFO database')
    host = absolute_directory(host_db, 'host package database')
    target = absolute_directory(target_db, 'target package database')
    if selected == target:
        raise ExportError('PKG_INFO database is the target package database')
    if selected != host:
        raise ExportError('PKG_INFO database is not the host package database')
    return words


class Exporter:
    def __init__(self, args, sha256_file):
        self.sha256_file = sha256_file
        self.args = args
        self.make_variables = make_variables(args.make_variable)
        self.native_make_variables = make_variables(
            getattr(args, 'native_make_variable', ()), '--native-make-variable')
        self.host_current = getattr(args, 'host_current', False)
        overlap = sorted(set(self.make_variables) & set(self.native_make_variables))
        if overlap:
            raise ExportError('conflicting --make-variable and --native-make-variable: ' + overlap[0])
        self.root = args.pkgsrc.resolve(strict=True)
        self.makeconf = args.makeconf.resolve(strict=True)
        self.bmake = args.bmake.resolve(strict=True)
        self.pkg_admin = args.pkg_admin.resolve(strict=True)
        # Ambient compiler and make variables must not select another graph.
        self.environment = {key: os.environ[key] for key in
                            ('PATH', 'HOME', 'TMPDIR', 'SYSTEMROOT')
                            if key in os.environ}
        self.environment['LC_ALL'] = 'C'
        self.nodes = {}
        self.metadata = {}
        self.contexts = {}
        self.patterns = {}
        self.pending = []
        self.test_requirements = []
        self.query_results = {}
        self.file_digests = {}
        self.package_bases = {}
        self.host_argv = None
        self.host_names = None

    def run(self, command, **kwargs):
        completed = subprocess.run(command, text=True, capture_output=True,
                                   timeout=self.args.timeout, **kwargs)
        if completed.returncode:
            # The debug inventory can contain private MAKECONF values.
            detail = ('bmake variable inventory query failed' if '-dg1' in command
                      else completed.stderr.strip()[:2000])
            raise ExportError('metadata command failed: ' + detail)
        return completed

    def package_path(self, path, parent=None):
        candidate = ((parent or self.root) / path).resolve(strict=True)
        relative = candidate.relative_to(self.root)
        if len(relative.parts) != 2 or not (candidate / 'Makefile').is_file():
            raise ExportError('expected an existing category/package path')
        return relative.as_posix()

    def query(self, package, cross, settings, environment, pattern):
        command = [str(self.bmake), '-C', str(self.root / package),
                   'MAKECONF=' + str(self.makeconf),
                   'USE_CROSS_COMPILE=' + cross, '_MAKEVARS_MK=defined']
        command += [key + '=' + value for key, value in self.make_variables.items()]
        # Native assignments stay off target queries. A Darwin SDK version that
        # satisfies a host compiler-rt guard must not enter NetBSD metadata.
        if cross == 'no':
            command += [key + '=' + value for key, value in self.native_make_variables.items()]
        command += [key + '=' + value for key, value in sorted(settings.items())]
        if pattern:
            command.append('PKGNAME_REQD=' + pattern)
        # pkgsrc's phony metadata goal keeps .TARGETS out of the default build phase.
        command.append('show-vars')
        queries = []
        for variable in VARIABLES:
            queries += ['-V', '${' + variable + '}']
        # bmake has no GNU .VARIABLES inventory. Its native input graph lists
        # defined names. Query their expanded values separately through -V.
        try:
            completed = self.run(command + ['-dg1'] + queries, env=environment)
        except ExportError:
            role = 'target' if cross == 'yes' else 'native'
            raise ExportError(f'bmake variable inventory query failed: {package} ({role})') from None
        if '#*** Global Variables:' not in completed.stderr:
            raise ExportError('bmake did not report its native variable inventory')
        extra_trees = sorted(set(re.findall(
            r'^(FILESDIR\.[^\s=]+)[ \t]*=', completed.stderr, re.MULTILINE)))
        if any(not re.fullmatch(r'FILESDIR\.[A-Za-z0-9_.-]+', name) for name in extra_trees):
            raise ExportError('unsupported FILESDIR variable name in native metadata')
        values = completed.stdout.splitlines()
        if len(values) != len(VARIABLES):
            raise ExportError('unexpected bmake metadata line count for ' + package)
        result = dict(zip(VARIABLES, values))
        if extra_trees:
            queries = []
            for variable in extra_trees:
                queries += ['-V', '${' + variable + '}']
            values = self.run(command + queries, env=environment).stdout.splitlines()
            if len(values) != len(extra_trees):
                raise ExportError('unexpected bmake FILESDIR line count for ' + package)
            result.update(zip(extra_trees, values))
        if not result['PKGNAME'] or not result['PKGVERSION']:
            raise ExportError('missing package identity: ' + package)
        if result['USE_CROSS_COMPILE'].lower() != cross:
            raise ExportError('MAKECONF did not preserve the selected cross role')
        if result['PKG_SKIP_REASON'] or result['PKG_FAIL_REASON']:
            raise ExportError('pkgsrc rejected ' + package + ': ' +
                              result['PKG_SKIP_REASON'] + result['PKG_FAIL_REASON'])
        return result

    def matches(self, pattern, name):
        completed = subprocess.run([str(self.pkg_admin), 'pmatch', pattern, name],
                                   env=self.environment, text=True,
                                   capture_output=True, timeout=self.args.timeout)
        if completed.returncode:
            raise ExportError('native pkg_admin rejected dependency ' +
                              pattern + ' for ' + name)

    def file_digest(self, path):
        path = Path(path)
        info = path.lstat()
        identity = (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                    info.st_mtime_ns, info.st_ctime_ns)
        cached = self.file_digests.get(path)
        if cached is None or cached[0] != identity:
            cached = (identity, self.sha256_file(path))
            self.file_digests[path] = cached
        return cached[1]

    def inputs(self, package, metadata):
        directory = self.root / package
        paths = set()
        logical_names = {}
        missing = []
        # Hash loaded includes, including shared recipe fragments and mk.conf.
        for value in shlex.split(metadata['.MAKE.MAKEFILES']):
            paths.add((directory / value).resolve(strict=True))
        if not paths:
            raise ExportError('bmake did not report loaded makefiles')
        for path in directory.iterdir():
            if path.is_file():
                paths.add(path.resolve(strict=True))
        for variable in ('DISTINFO_FILE', 'PLIST_SRC'):
            for value in shlex.split(metadata[variable]):
                path = (directory / value).resolve()
                if path.is_file():
                    paths.add(path)
                else:
                    missing.append(variable + ':' + value)
        trees = ['PATCHDIR', 'FILESDIR', 'LOCALPATCHES']
        trees += sorted(name for name in metadata if name.startswith('FILESDIR.'))
        for variable in trees:
            value = metadata[variable]
            if variable == 'LOCALPATCHES' and value:
                value = str(Path(value) / package)
            if not value:
                continue
            tree = (directory / value).resolve()
            if tree.is_dir():
                for path in tree.rglob('*'):
                    if path.is_symlink() and path.is_dir():
                        raise ExportError('directory symlink in package inputs')
                    if path.is_file():
                        resolved = path.resolve(strict=True)
                        paths.add(resolved)
                        logical_names.setdefault(resolved, set()).add(
                            variable + '/' + path.relative_to(tree).as_posix())
        records = []
        for path in sorted(paths):
            checksum = self.file_digest(path)
            try:
                name = path.relative_to(self.root).as_posix()
            except ValueError:
                # External paths remain private. Their content still binds the lock.
                name = 'external:' + checksum
            records.append([name, checksum])
            for logical in sorted(logical_names.get(path, ())):
                records.append([logical, checksum])
        return digest(canonical({'files': sorted(records), 'missing': sorted(missing), 'metadata': metadata}))

    def visit(self, package, cross, settings, environment, pattern=None):
        identity = self.node_identity(package, cross, settings)
        context = self.query_context(cross, settings, environment)
        if identity in self.nodes:
            if self.contexts[identity] != context:
                raise ExportError('conflicting recursive contexts for ' + identity)
            if pattern:
                self.matches(pattern, self.metadata[identity]['PKGNAME'])
                if pattern not in self.patterns[identity]:
                    candidate = self.query_result(package, cross, settings, environment, pattern)
                    if (candidate != self.metadata[identity] or
                            self.inputs(package, candidate) != self.nodes[identity]['input_sha256']):
                        raise ExportError('conflicting package variants for ' + identity)
                    self.patterns[identity].add(pattern)
            return identity
        if len(self.nodes) >= self.args.max_nodes:
            raise ExportError('dependency closure exceeds --max-nodes')
        metadata = self.query_result(package, cross, settings, environment, pattern)
        if pattern:
            self.matches(pattern, metadata['PKGNAME'])
        expected_arch = {'amd64': 'x86_64'}.get(self.args.target, self.args.target)
        if (cross == 'yes' or self.args.mode == 'native') and metadata['MACHINE_ARCH'] != expected_arch:
            raise ExportError('target architecture differs from native bmake metadata')
        if cross == 'yes' and metadata['MACHINE_GNU_PLATFORM'] != self.args.triplet:
            raise ExportError('target triplet differs from native bmake metadata')
        if cross == 'no' and self.args.mode == 'native' and metadata['MACHINE_GNU_PLATFORM'] != self.args.triplet:
            raise ExportError('native triplet differs from native bmake metadata')
        node = {'id': identity, 'version': metadata['PKGVERSION'],
                'input_sha256': self.inputs(package, metadata), 'dependencies': []}
        self.nodes[identity] = node
        self.metadata[identity] = metadata
        self.contexts[identity] = context
        self.patterns[identity] = {pattern} if pattern else set()
        # Queue traversal instead of Python recursion for large source closures.
        self.pending.append((identity, package, cross, settings, environment, metadata))
        return identity

    def node_identity(self, package, cross, settings):
        role = 'target' if cross == 'yes' else 'host'
        identity = role + ':' + package
        if settings:
            identity += '@' + digest(canonical(settings))[:16]
        return identity

    def query_context(self, cross, settings, environment):
        context = [cross, settings, environment, self.make_variables]
        if cross == 'no' and self.native_make_variables:
            context.append(self.native_make_variables)
        return context

    def query_key(self, package, cross, settings, environment, pattern):
        native = tuple(self.native_make_variables.items()) if cross == 'no' else ()
        return (package, cross, tuple(sorted(settings.items())), tuple(sorted(environment.items())),
                tuple(self.make_variables.items()), native, pattern)

    def query_result(self, package, cross, settings, environment, pattern):
        key = self.query_key(package, cross, settings, environment, pattern)
        if key not in self.query_results:
            return self.query(package, cross, settings, environment, pattern)
        return self.query_results[key]

    def dependency_requests(self, parent):
        identity, package, cross, settings, environment, metadata = parent
        recursive_env = dict(environment)
        recursive_env.update(assignments(metadata['PKGSRC_MAKE_ENV']))
        recursive_env['PATH'] = metadata['_PATH_ORIG']
        for key in list(recursive_env):
            if key in ('MAKEFLAGS', '_PKGSRC_BARRIER', 'PKGNAME_REQD', 'MAKECONF') or key.startswith('TARGET_'):
                recursive_env.pop(key)
        # A current host package keeps the packages it still provides. Its own
        # build tools are not part of this graph; cross-bulk does not schedule them.
        current = self.host_node_is_current(package, cross, settings, environment, metadata)
        children = []
        for variable, kind in DEPENDENCIES.items():
            if current and variable not in ('DEPENDS', 'TEST_DEPENDS'):
                continue
            if self.args.dependency_phase == 'runtime' and kind != 'runtime':
                continue
            for dependency in sorted(set(shlex.split(metadata[variable]))):
                pattern, sep, path = dependency.partition(':')
                if not sep or not pattern or not path:
                    raise ExportError('invalid native dependency entry')
                child = self.package_path(path, self.root / package)
                if kind == 'test' and self.args.dependency_phase == 'build':
                    self.test_requirements.append({
                        'owner': identity, 'role': 'target' if cross == 'yes' else 'host',
                        'package_path': child, 'pattern': pattern})
                    continue
                if current and kind == 'test':
                    continue
                child_cross = 'no' if kind == 'tool' else cross
                # Follow pkgformat/pkg/depends.mk, including TEST_DEPENDS.
                child_settings = assignments(metadata['CROSSTARGETSETTINGS']) if kind == 'tool' and cross == 'yes' else {}
                if any(not key.startswith('TARGET_') for key in child_settings):
                    raise ExportError('unexpected CROSSTARGETSETTINGS key')
                children.append(((child, child_cross, child_settings, recursive_env, pattern), kind))
        return children

    def merge_children(self, identity, children):
        edges = set()
        for request, kind in children:
            child_id = self.visit(*request)
            edges.add((child_id, kind))
        self.nodes[identity]['dependencies'] = [
            {'id': child, 'kind': kind} for child, kind in sorted(edges)]

    def prefetch(self, requests):
        """Run all unseen exact metadata requests for one deterministic frontier."""
        unique = []
        pending_contexts = {}
        queued_keys = set()
        for request in requests:
            package, cross, settings, environment, pattern = request
            identity = self.node_identity(package, cross, settings)
            context = self.query_context(cross, settings, environment)
            if identity in self.contexts:
                if self.contexts[identity] != context:
                    raise ExportError('conflicting recursive contexts for ' + identity)
            else:
                if identity in pending_contexts and pending_contexts[identity] != context:
                    raise ExportError('conflicting recursive contexts for ' + identity)
                pending_contexts.setdefault(identity, context)
                if len(self.nodes) + len(pending_contexts) > self.args.max_nodes:
                    raise ExportError('dependency closure exceeds --max-nodes')
            key = self.query_key(package, cross, settings, environment, pattern)
            if key not in self.query_results and key not in queued_keys:
                queued_keys.add(key)
                unique.append(request)
        if not unique:
            return
        if self.args.jobs == 1:
            results = [self.query(*request) for request in unique]
        else:
            results = []
            with ThreadPoolExecutor(max_workers=min(self.args.jobs, len(unique))) as pool:
                futures = [pool.submit(self.query, *request) for request in unique]
                try:
                    # Consume in request order so graph mutation and failures stay deterministic.
                    results = [future.result() for future in futures]
                except BaseException:
                    for future in futures:
                        future.cancel()
                    raise
        for request, metadata in zip(unique, results):
            self.query_results[self.query_key(*request)] = metadata

    def parallel_frontier(self):
        roots = [self.package_path(root) for root in sorted(set(self.args.root))]
        root_requests = [(package, 'yes' if self.args.mode == 'cross' else 'no', {},
                          self.environment, None) for package in roots]
        self.prefetch(root_requests)
        for request in root_requests:
            self.visit(*request)

        while self.pending:
            frontier, self.pending = self.pending, []
            plans = []
            requests = []
            for parent in frontier:
                identity = parent[0]
                children = self.dependency_requests(parent)
                plans.append((identity, children))
                requests.extend(request for request, _ in children)
            self.prefetch(requests)
            for identity, children in plans:
                self.merge_children(identity, children)

    def frozen_show_var(self, variable, *, native=None, cross=None):
        command = [str(self.bmake), '-C', str(self.root / 'pkgtools/pkg_install'),
                   'MAKECONF=' + str(self.makeconf), '_MAKEVARS_MK=defined']
        if native is not None:
            command.append('EMBERBSD_NATIVE_TOOLSET_VERIFIED=' + native)
        if cross is not None:
            command.append('USE_CROSS_COMPILE=' + cross)
        command += ['show-var', 'VARNAME=' + variable]
        lines = self.run(command, env=self.environment).stdout.splitlines()
        if len(lines) != 1 or lines[0] == '':
            raise ExportError('invalid ' + variable + ' from frozen MAKECONF')
        return lines[0]

    def discover_host_pkg_info(self):
        native = self.frozen_show_var('EMBERBSD_NATIVE_TOOLSET_VERIFIED')
        if any(character.isspace() for character in native):
            raise ExportError('invalid EMBERBSD_NATIVE_TOOLSET_VERIFIED from frozen MAKECONF')
        info = self.frozen_show_var('PKG_INFO', native=native, cross='no')
        host_db = self.frozen_show_var('_HOST_PKG_DBDIR', native=native, cross='no')
        target_db = self.frozen_show_var('_PKG_DBDIR', native=native)
        return host_pkg_info_argv(info, host_db, target_db)

    def host_pkgnames(self):
        completed = self.run(self.host_argv + ['-a', '-Q', 'PKGNAME'], env=self.environment)
        names = completed.stdout.splitlines()
        if any(not name or any(character.isspace() for character in name) for name in names):
            raise ExportError('invalid host PKGNAME listing')
        if len(names) != len(set(names)):
            raise ExportError('duplicate host PKGNAME')
        return tuple(sorted(names))

    def package_base(self, package, cross, settings, environment):
        key = (package, cross, tuple(sorted(settings.items())))
        if key not in self.package_bases:
            command = [str(self.bmake), '-C', str(self.root / package),
                       'MAKECONF=' + str(self.makeconf),
                       'USE_CROSS_COMPILE=' + cross, '_MAKEVARS_MK=defined']
            command += [name + '=' + value for name, value in self.make_variables.items()]
            if cross == 'no':
                command += [name + '=' + value for name, value in self.native_make_variables.items()]
            command += [name + '=' + value for name, value in sorted(settings.items())]
            command += ['show-var', 'VARNAME=PKGBASE']
            lines = self.run(command, env=environment).stdout.splitlines()
            if len(lines) != 1 or lines[0] == '' or any(character.isspace() for character in lines[0]):
                raise ExportError('missing PKGBASE for ' + package)
            self.package_bases[key] = lines[0]
        return self.package_bases[key]

    def host_is_current(self, base, name):
        pattern = native_current_pattern(base, name)
        completed = subprocess.run(self.host_argv + ['-e', pattern], env=self.environment,
                                   text=True, capture_output=True, timeout=self.args.timeout)
        if completed.returncode == 0:
            return True
        if completed.returncode == 1:
            return False
        raise ExportError('pkg_info -e failed with status ' + str(completed.returncode))

    def host_node_is_current(self, package, cross, settings, environment, metadata):
        if not self.host_current or cross != 'no':
            return False
        return self.host_is_current(self.package_base(package, cross, settings, environment),
                                    metadata['PKGNAME'])

    def export(self):
        if self.host_current:
            self.host_argv = self.discover_host_pkg_info()
            self.host_names = self.host_pkgnames()
        if self.args.jobs > 1:
            self.parallel_frontier()
        else:
            for root in sorted(set(self.args.root)):
                self.visit(self.package_path(root),
                           'yes' if self.args.mode == 'cross' else 'no', {}, self.environment)
            while self.pending:
                parent = self.pending.pop(0)
                self.merge_children(parent[0], self.dependency_requests(parent))
        if self.host_argv is not None and self.host_pkgnames() != self.host_names:
            raise ExportError('host package database changed during export')
        for identity, node in self.nodes.items():
            node['input_sha256'] = digest(canonical({
                'inputs': node['input_sha256'], 'query_context': self.contexts[identity],
                'required_patterns': sorted(self.patterns[identity])}))
        shared = {'makeconf': self.file_digest(self.makeconf), 'bmake': self.file_digest(self.bmake),
                  'pkg_admin': self.file_digest(self.pkg_admin),
                  'dependency-phase': digest(self.args.dependency_phase.encode()),
                  'make-variables': digest(canonical(self.make_variables)),
                  'environment': digest(canonical(self.environment)),
                  'exporter': self.file_digest(Path(__file__))}
        if self.native_make_variables:
            shared['native-make-variables'] = digest(canonical(self.native_make_variables))
        if self.host_argv is not None:
            shared['host-pkg-info-argv'] = digest(canonical(self.host_argv))
            shared['host-pkg-info-binary'] = self.file_digest(self.host_argv[0])
            shared['host-pkg-names'] = digest(canonical(list(self.host_names)))
        for item in self.args.shared_input:
            name, sep, path = item.partition('=')
            if not sep or not re.fullmatch(r'[a-zA-Z0-9_.-]+', name) or name in shared:
                raise ExportError('invalid or duplicate --shared-input name')
            shared[name] = self.file_digest(path)
        def summary(variables):
            return ', '.join(key + '=' + value for key, value in variables.items()) or 'none'
        source = ('pkgsrc native metadata (' + self.args.mode +
                  '; dependency phase ' + self.args.dependency_phase +
                  '; make variables: ' + summary(self.make_variables))
        if self.native_make_variables:
            source += '; native make variables: ' + summary(self.native_make_variables)
        if self.host_current:
            source += '; host current package database'
        return {'schema': 'ports-graph-v1',
                'context': {'target': self.args.target, 'triplet': self.args.triplet,
                            'toolchain_sha256': self.file_digest(self.args.toolchain_input),
                            'base_sha256': self.file_digest(self.args.base_input),
                            'shared_inputs': shared},
                'provenance': {'source': source + ')',
                               'revision': self.args.revision},
                'nodes': [self.nodes[key] for key in sorted(self.nodes)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'pkgsrc', 'makeconf', 'bmake', 'pkg-admin', 'toolchain-input', 'base-input'):
        parser.add_argument('--' + name, required=True, type=Path)
    for name in ('target', 'triplet', 'revision'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--mode', choices=('cross', 'native'), default='cross')
    parser.add_argument('--dependency-phase', choices=('all', 'build', 'runtime'), default='all',
                        help='build records tests separately; runtime exports only installed dependencies')
    parser.add_argument('--test-requirements-output', type=Path,
                        help='mandatory pending TEST_DEPENDS inventory for the build phase')
    parser.add_argument('--diagnostic-graph', type=Path,
                        help='write the raw graph here only if SDK locking fails')
    parser.add_argument('--root', action='append', required=True, help='category/package; repeat for each root')
    parser.add_argument('--shared-input', action='append', default=[], metavar='NAME=FILE')
    parser.add_argument('--make-variable', action='append', default=[], metavar='NAME=VALUE',
                        help='repeatable scalar bmake assignment for every query; does not accept targets or make flags')
    parser.add_argument('--native-make-variable', action='append', default=[], metavar='NAME=VALUE',
                        help='repeatable scalar assignment for native role queries only, including their native dependencies')
    parser.add_argument('--host-current', action='store_true',
                        help='ask the frozen MAKECONF host pkg_info which native packages are current')
    parser.add_argument('--max-nodes', type=int, default=1000)
    parser.add_argument('--jobs', type=int, default=1,
                        help='maximum concurrent bmake metadata queries (default: 1)')
    parser.add_argument('--timeout', type=int, default=120, help='seconds per metadata command')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.max_nodes < 1 or args.jobs < 1 or args.timeout < 1:
            raise ExportError('limits must be positive')
        if (args.dependency_phase == 'build') != bool(args.test_requirements_output):
            raise ExportError('build phase requires --test-requirements-output; other phases forbid it')
        outputs = [args.output] + ([args.test_requirements_output] if args.test_requirements_output else [])
        if args.diagnostic_graph:
            outputs.append(args.diagnostic_graph)
        if len({path.resolve() for path in outputs}) != len(outputs):
            raise ExportError('output paths must be distinct')
        if any(path.exists() or path.is_symlink() for path in outputs):
            raise ExportError('output paths must not exist')
        sdk_source = args.sdk_source.resolve(strict=True) / 'src'
        if not (sdk_source / 'emberbsd_sdk' / 'ports_plan.py').is_file():
            raise ExportError('--sdk-source must contain the SDK Ports planner')
        sys.path.insert(0, str(sdk_source))
        from emberbsd_sdk import ports_plan as sdk
        from emberbsd_sdk.errors import SDKError
        from emberbsd_sdk.inventory import sha256_file
        from emberbsd_sdk.jsonio import json_bytes, write_json
        if getattr(sdk, 'PORTS_PLAN_API', None) != 1:
            raise ExportError('unsupported SDK PORTS_PLAN_API; expected 1')
        try:
            exporter = Exporter(args, sha256_file)
            graph = exporter.export()
            try:
                sdk.lock_graph(graph)
            except SDKError:
                if args.diagnostic_graph:
                    write_json(str(args.diagnostic_graph), graph, exclusive=True)
                raise
            if len(json_bytes(graph)) > sdk.PORTS_JSON_LIMIT:
                raise ExportError('graph exceeds the SDK JSON size limit')
            if args.test_requirements_output:
                inventory = {'schema': 'ports-test-requirements-v1', 'phase': 'build',
                             'graph_sha256': digest(json_bytes(graph)),
                             'status': 'test-depends-and-tests-pending',
                             'requirements': sorted(exporter.test_requirements,
                                 key=lambda row: (row['owner'], row['package_path'], row['pattern']))}
                if len(json_bytes(inventory)) > sdk.PORTS_JSON_LIMIT:
                    raise ExportError('test requirements exceed the SDK JSON size limit')
                write_json(str(args.test_requirements_output), inventory, exclusive=True)
            write_json(str(args.output), graph, exclusive=True)
        except SDKError as error:
            raise ExportError(str(error)) from error
    except (OSError, ValueError, ImportError, subprocess.SubprocessError) as error:
        parser.exit(1, 'export-build-graph: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
