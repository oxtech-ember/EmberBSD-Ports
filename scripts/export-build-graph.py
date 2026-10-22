#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted native metadata adapter.
"""Export a bounded pkgsrc dependency closure through native bmake metadata."""

import argparse
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


class Exporter:
    def __init__(self, args, sha256_file):
        self.sha256_file = sha256_file
        self.args = args
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
                   'USE_CROSS_COMPILE=' + cross]
        command += [key + '=' + value for key, value in sorted(settings.items())]
        if pattern:
            command.append('PKGNAME_REQD=' + pattern)
        queries = []
        for variable in VARIABLES:
            queries += ['-V', '${' + variable + '}']
        # bmake has no GNU .VARIABLES inventory. Its native input graph lists
        # defined names. Query their expanded values separately through -V.
        completed = self.run(command + ['-dg1'] + queries, env=environment)
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
            checksum = self.sha256_file(path)
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
        role = 'target' if cross == 'yes' else 'host'
        identity = role + ':' + package
        if settings:
            identity += '@' + digest(canonical(settings))[:16]
        context = [cross, settings, environment]
        if identity in self.nodes:
            if self.contexts[identity] != context:
                raise ExportError('conflicting recursive contexts for ' + identity)
            if pattern:
                self.matches(pattern, self.metadata[identity]['PKGNAME'])
                if pattern not in self.patterns[identity]:
                    candidate = self.query(package, cross, settings, environment, pattern)
                    if (candidate != self.metadata[identity] or
                            self.inputs(package, candidate) != self.nodes[identity]['input_sha256']):
                        raise ExportError('conflicting package variants for ' + identity)
                    self.patterns[identity].add(pattern)
            return identity
        if len(self.nodes) >= self.args.max_nodes:
            raise ExportError('dependency closure exceeds --max-nodes')
        metadata = self.query(package, cross, settings, environment, pattern)
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

    def export(self):
        for root in sorted(set(self.args.root)):
            self.visit(self.package_path(root),
                       'yes' if self.args.mode == 'cross' else 'no', {}, self.environment)
        while self.pending:
            identity, package, cross, settings, environment, metadata = self.pending.pop(0)
            recursive_env = dict(environment)
            recursive_env.update(assignments(metadata['PKGSRC_MAKE_ENV']))
            recursive_env['PATH'] = metadata['_PATH_ORIG']
            for key in list(recursive_env):
                if key in ('MAKEFLAGS', '_PKGSRC_BARRIER', 'PKGNAME_REQD', 'MAKECONF') or key.startswith('TARGET_'):
                    recursive_env.pop(key)
            edges = set()
            for variable, kind in DEPENDENCIES.items():
                for dependency in sorted(set(shlex.split(metadata[variable]))):
                    pattern, sep, path = dependency.partition(':')
                    if not sep or not pattern or not path:
                        raise ExportError('invalid native dependency entry')
                    child = self.package_path(path, self.root / package)
                    child_cross = 'no' if kind == 'tool' else cross
                    # Follow pkgformat/pkg/depends.mk, including TEST_DEPENDS.
                    child_settings = assignments(metadata['CROSSTARGETSETTINGS']) if kind == 'tool' and cross == 'yes' else {}
                    if any(not key.startswith('TARGET_') for key in child_settings):
                        raise ExportError('unexpected CROSSTARGETSETTINGS key')
                    child_id = self.visit(child, child_cross, child_settings, recursive_env, pattern)
                    edges.add((child_id, kind))
            self.nodes[identity]['dependencies'] = [
                {'id': child, 'kind': kind} for child, kind in sorted(edges)]
        for identity, node in self.nodes.items():
            node['input_sha256'] = digest(canonical({
                'inputs': node['input_sha256'], 'query_context': self.contexts[identity],
                'required_patterns': sorted(self.patterns[identity])}))
        shared = {'makeconf': self.sha256_file(self.makeconf), 'bmake': self.sha256_file(self.bmake),
                  'pkg_admin': self.sha256_file(self.pkg_admin),
                  'environment': digest(canonical(self.environment)),
                  'exporter': self.sha256_file(Path(__file__))}
        for item in self.args.shared_input:
            name, sep, path = item.partition('=')
            if not sep or not re.fullmatch(r'[a-zA-Z0-9_.-]+', name) or name in shared:
                raise ExportError('invalid or duplicate --shared-input name')
            shared[name] = self.sha256_file(path)
        return {'schema': 'ports-graph-v1',
                'context': {'target': self.args.target, 'triplet': self.args.triplet,
                            'toolchain_sha256': self.sha256_file(self.args.toolchain_input),
                            'base_sha256': self.sha256_file(self.args.base_input),
                            'shared_inputs': shared},
                'provenance': {'source': 'pkgsrc native metadata (' + self.args.mode + ')',
                               'revision': self.args.revision},
                'nodes': [self.nodes[key] for key in sorted(self.nodes)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'pkgsrc', 'makeconf', 'bmake', 'pkg-admin', 'toolchain-input', 'base-input'):
        parser.add_argument('--' + name, required=True, type=Path)
    for name in ('target', 'triplet', 'revision'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--mode', choices=('cross', 'native'), default='cross')
    parser.add_argument('--root', action='append', required=True, help='category/package; repeat for each root')
    parser.add_argument('--shared-input', action='append', default=[], metavar='NAME=FILE')
    parser.add_argument('--max-nodes', type=int, default=1000)
    parser.add_argument('--timeout', type=int, default=120, help='seconds per metadata command')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.max_nodes < 1 or args.timeout < 1:
            raise ExportError('limits must be positive')
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
            graph = Exporter(args, sha256_file).export()
            sdk.lock_graph(graph)
            if len(json_bytes(graph)) > sdk.PORTS_JSON_LIMIT:
                raise ExportError('graph exceeds the SDK JSON size limit')
            write_json(str(args.output), graph, exclusive=True)
        except SDKError as error:
            raise ExportError(str(error)) from error
    except (OSError, ValueError, ImportError, subprocess.SubprocessError) as error:
        parser.exit(1, 'export-build-graph: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
