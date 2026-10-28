#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Ported from target-query.rb.
"""Run GI queries against real EmberBSD target libraries with SDK API 1."""

import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True

from sdk_source import install_signal_handlers, load_sdk

TARGETS = {'aarch64': ('aarch64', 183), 'amd64': ('x86_64', 62)}
REMOTE_DIRECTORY = re.compile(r'/tmp/ember-gir\.[A-Za-z0-9]{8}')
XML_LIMIT = 16 * 1024 * 1024


class QueryError(Exception):
    """A GI policy or transport check refused the query."""


def require(condition, message):
    if not condition:
        raise QueryError(message)


def transfer_timeout(config):
    value = config.get('transfer_timeout_seconds', 180)
    require(type(value) is int and 0 < value <= 3600,
            'transfer_timeout_seconds must be an integer from 1 to 3600')
    return value


def ssh_command(config):
    """Build transport argv; legacy configs may still use PATH lookup."""
    from emberbsd_sdk.paths import canonical_existing, regular_file

    host = config.get('ssh')
    require(isinstance(host, str) and re.fullmatch(r'(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*', host),
            'invalid SSH destination')
    command = 'ssh'
    if 'ssh_executable' in config:
        selected = config['ssh_executable']
        require(isinstance(selected, str) and os.path.isabs(selected), 'SSH executable must be absolute')
        command = canonical_existing(selected)
        regular_file(command)
        require(os.access(command, os.X_OK), 'SSH executable is not executable')
    argv = [command, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=5', '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3']
    if 'ssh_config' in config:
        selected = config['ssh_config']
        require(isinstance(selected, str) and os.path.isabs(selected), 'SSH config must be absolute')
        selected = canonical_existing(selected)
        regular_file(selected)
        argv += ['-F', selected]
    if 'ssh_port' in config:
        port = config['ssh_port']
        require(type(port) is int and 1 <= port <= 65535, 'invalid SSH port')
        argv += ['-p', str(port)]
    if 'host_key_alias' in config:
        alias = config['host_key_alias']
        require(isinstance(alias, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', alias), 'invalid host key alias')
        argv += ['-o', 'HostKeyAlias=' + alias]
    return [*argv, host]


class FailureMarker:
    """Keep the first incomplete execute query visible to configure."""

    def __init__(self, path):
        self.path = path
        self.complete = False

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        if self.path is not None and not self.complete:
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                return
            with os.fdopen(fd, 'wb') as output:
                output.write(b'Target query did not complete with verified execution and cleanup.\n')


def query(arguments):
    # SDK selection happens in main before any SDK import or producer starts.
    from emberbsd_sdk.elf import read_elf_dynamic
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError, SDKError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json, write_json
    from emberbsd_sdk.paths import (canonical_existing, real_directory, regular_file, relative_inside,
                                   open_regular, stable_identity, verify_stable, entry)
    from emberbsd_sdk import stream

    require(getattr(stream, 'PRODUCER_STREAM_API', None) == 1,
            'selected SDK lacks producer stream API 1')
    require(getattr(stream, 'PRODUCER_INPUT_API', None) == 1,
            'selected SDK lacks producer input API 1')
    require(getattr(stream, 'PRODUCER_INSPECTION_API', None) == 1,
            'selected SDK lacks producer inspection API 1')
    config = read_json(os.environ['EMBERBSD_GI_QUERY_CONFIG'])
    require(isinstance(config, dict), 'GI query configuration must be an object')
    transfer_timeout_seconds = transfer_timeout(config)
    target = config.get('target', 'aarch64')
    require(isinstance(target, str) and target in TARGETS, 'unsupported GI target')
    processor, machine = TARGETS[target]
    layout = config.get('executable_layout', 'flat')
    require(isinstance(layout, str) and layout in ('flat', 'prefix-bin'),
            'unsupported executable layout')
    query_relative = 'query' if layout == 'flat' else 'bin/query'
    library_inputs = config.get('library_inputs', [])
    require(isinstance(library_inputs, list) and len(library_inputs) <= 32,
            'library_inputs must be a bounded array')
    def library_name(value):
        return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.+-]{0,254}', value)
    input_names = set()
    for item in library_inputs:
        require(isinstance(item, dict) and set(item) == {'name', 'sha256'}, 'invalid library input entry')
        require(library_name(item['name']) and item['name'] not in input_names,
                'unsafe or duplicate library input name')
        require(isinstance(item['sha256'], str) and re.fullmatch('[0-9a-f]{64}', item['sha256']),
                'invalid library input SHA256')
        input_names.add(item['name'])
    require('EMBERBSD_GI_TARGET' not in os.environ or os.environ['EMBERBSD_GI_TARGET'] == target,
            'configuration differs from recipe target')

    def absolute(key):
        value = config[key]
        require(isinstance(value, str) and value.startswith('/'), f'{key} must be absolute')
        return canonical_existing(value)

    # Keep the legacy readelf configuration and --check identity contract.
    # SDK API 1 reads target ELF bytes directly; it does not invoke this tool.
    base, sysroot, cache, readelf = (absolute(key) for key in ('build_root', 'sysroot', 'cache', 'readelf'))
    for directory in (base, sysroot, cache):
        real_directory(directory)
    regular_file(readelf)
    require(os.access(readelf, os.X_OK), 'readelf is not executable')
    roots = (base, sysroot)

    def within(path, root):
        return relative_inside(path, root) is not None

    require(not within(base, sysroot) and not within(sysroot, base), 'build/sysroot overlap')
    require(not within(cache, sysroot) and not within(sysroot, cache), 'cache overlaps providers')
    ssh = ssh_command(config)
    if arguments and arguments[0] == '--check':
        require(len(arguments) in (4, 5), 'usage: --check WORKDIR SYSROOT READELF [aarch64|amd64]')
        expected_target = arguments[4] if len(arguments) == 5 else 'aarch64'
        workdir, target_root, tool = map(canonical_existing, arguments[1:4])
        require(within(workdir, base) and target_root == sysroot and tool == readelf and expected_target == target,
                'configuration differs from recipe')
        print('PASS: GI query configuration matches the selected work, sysroot and readelf')
        return 0

    execute = bool(arguments and arguments[0] == '--execute')
    if execute:
        arguments = arguments[1:]
    inputs = config.get('execute_inputs', [])
    resource_env = config.get('execute_environment', {})
    require(isinstance(inputs, list) and len(inputs) <= 1024, 'execute_inputs must be a bounded array')
    require(isinstance(resource_env, dict) and len(resource_env) <= 32, 'execute_environment must be a bounded object')
    require(execute or not (inputs or resource_env), 'data inputs require --execute')
    artifacts, destinations, data_paths, data_bytes = [], set(), set(), 0
    data_roots = {root: real_directory(root) for root in roots} if inputs else {}

    def verify_data_roots():
        for root, info in data_roots.items():
            require(canonical_existing(root) == root and
                    stable_identity(real_directory(root))[:3] == stable_identity(info)[:3],
                    'data root identity changed')

    def data_path(value):
        require(isinstance(value, str) and len(value.encode('utf-8')) <= 512 and
                re.fullmatch(r'data(?:/[A-Za-z0-9_+.-]+)+', value) and
                all(part not in ('.', '..') for part in value.split('/')), 'unsafe data destination')
        return value

    for item in inputs:
        require(isinstance(item, dict) and set(item) == {'source', 'path', 'sha256'}, 'invalid data input entry')
        path = data_path(item['path'])
        require(not any(path == other or path.startswith(other + '/') or other.startswith(path + '/')
                        for other in destinations), 'colliding data destination')
        destinations.add(path)
        source, expected = item['source'], item['sha256']
        require(isinstance(source, str) and source.startswith('/') and canonical_existing(source) == source,
                'data source requires canonical real ancestors')
        require(any(within(source, root) for root in roots), 'data source outside target/build roots')
        info = regular_file(source)
        require(isinstance(expected, str) and re.fullmatch(r'[0-9a-f]{64}', expected), 'invalid data SHA256')
        require(info.st_size <= 16 * 1024 * 1024, 'data file exceeds 16 MiB')
        data_bytes += info.st_size
        require(data_bytes <= 64 * 1024 * 1024, 'data inputs exceed 64 MiB')
        require(sha256_file(source) == expected, 'data input SHA256 differs')
        verify_stable(source, info)
        artifacts.append((source, path, expected, info))
        current = Path(path)
        data_paths.add(path)
        data_paths.update(parent.as_posix() for parent in current.parents if parent.as_posix() != '.')
    for name, value in resource_env.items():
        require(isinstance(name, str) and re.fullmatch(r'CSF_[A-Za-z][A-Za-z0-9_]{0,59}', name),
                'only bounded CSF resource environment names are supported')
        require(isinstance(value, dict) and len(value) == 1, 'invalid resource environment value')
        if name == 'CSF_LANGUAGE':
            require(set(value) == {'literal'} and isinstance(value['literal'], str) and
                    re.fullmatch(r'[A-Za-z0-9_+.-]{1,32}', value['literal']), 'invalid CSF language literal')
        else:
            require(set(value) == {'stage_path'} and isinstance(value['stage_path'], str) and
                    value['stage_path'] in data_paths, 'resource environment path has no declared data')
    marker = None
    if execute and 'EMBERBSD_GI_FAILURE_MARKER' in os.environ:
        marker = os.environ['EMBERBSD_GI_FAILURE_MARKER']
        require(marker.startswith('/') and within(canonical_existing(os.path.dirname(marker)), base)
                and not os.path.islink(marker), 'failure marker outside build root')
        marker = os.path.join(canonical_existing(os.path.dirname(marker)), os.path.basename(marker))

    with FailureMarker(marker) as failure:
        require(bool(arguments), 'binary required')
        program, *args = arguments
        # Waf base commands use the sysroot's regular file, never target PATH.
        # They execute as query; do not allow argv[0]-dependent base utilities.
        commands = {'getconf': '/usr/bin/getconf'}
        if '/' not in program:
            require(execute and program in commands, f'unsupported target command: {program}')
            exe = sysroot + commands[program]
            require(os.path.isfile(exe), f'target command missing from sysroot: {program}')
            require(not os.path.islink(exe) and canonical_existing(exe) == exe,
                    f'target command is not a sysroot regular file: {program}')
        else:
            exe = canonical_existing(program)
            require(within(exe, base), 'binary outside build root')
        require(execute or not args or (len(args) == 1 and args[0].startswith('--introspect-dump=')),
                'only an optional introspect-dump argument is supported')
        in_path = out_path = None
        if not execute and args:
            paths = args[0].removeprefix('--introspect-dump=').split(',', 1)
            require(len(paths) == 2 and all(path.startswith('/') for path in paths), 'invalid dump paths')
            in_path = canonical_existing(paths[0])
            parent = canonical_existing(os.path.dirname(paths[1]))
            require(within(in_path, base) and within(parent, base), 'dump paths outside build root')
            out_path = os.path.join(parent, os.path.basename(paths[1]))
            require(not os.path.lexists(out_path), 'dump output already exists')

        work = Path(tempfile.mkdtemp(prefix='gi-query-', dir=cache))
        stage = work / 'stage'
        (stage / 'lib').mkdir(parents=True)
        environment = dict(os.environ)

        def completed(command, data=None, *, timeout=180):
            try:
                result = stream.capture_streamed(command, env=environment, input=data,
                                                timeout=timeout, stdout_limit=16 * 1024 * 1024,
                                                empty_snapshot_timeout=30)
                require(not result.stderr_truncated, 'host command stderr exceeds capture limit')
                return subprocess.CompletedProcess(command, 0, result.value, result.stderr)
            except CommandError as error:
                require(not error.stdout_truncated and not error.stderr_truncated,
                        'host command output exceeds capture limit')
                return subprocess.CompletedProcess(command, error.returncode, error.stdout, error.stderr)

        def run(name, command, data=None, *, timeout=180):
            try:
                result = completed(command, data, timeout=timeout)
            except ProcessOwnershipError:
                raise
            except SDKError as error:
                (work / (name + '.log')).write_text(
                    f'refused: {error}\ntimeout_seconds={timeout}\n'
                    f'input_bytes={0 if data is None else len(data)}\n', encoding='utf-8')
                raise
            output = result.stdout + result.stderr
            (work / (name + '.log')).write_bytes(output)
            require(result.returncode == 0, f'{name} failed ({result.returncode}); see {work}')
            return output

        def mapdir(path):
            require(isinstance(path, str), 'library directories must be strings')
            if os.path.isdir(path):
                resolved = canonical_existing(path)
                if any(within(resolved, root) for root in roots):
                    return resolved
            if any(within(path, root) for root in roots):
                return path
            return sysroot + path if path.startswith('/') else os.path.abspath(path)

        configured = config.get('library_dirs', [])
        require(isinstance(configured, list) and all(isinstance(path, str) for path in configured),
                'library_dirs must be an array of strings')
        search = list(dict.fromkeys(mapdir(path) for path in configured + environment.get('LD_LIBRARY_PATH', '').split(':') if path))
        defaults = [mapdir(path) for path in ('/usr/pkg/gcc16/lib', '/usr/pkg/lib', '/usr/lib', '/lib')]
        files, pending, declared_libraries = {}, [exe], []
        library_root = real_directory(sysroot) if library_inputs else None
        sdk_directories = []
        if library_inputs:
            for suffix in ('/usr/pkg/gcc16/lib', '/usr/pkg/lib', '/usr/lib', '/lib'):
                path = sysroot + suffix
                if os.path.isdir(path):
                    path = canonical_existing(path)
                    require(within(path, sysroot), 'SDK library directory escapes sysroot')
                    real_directory(path)
                    if path not in sdk_directories:
                        sdk_directories.append(path)
        for item in library_inputs:
            matches = [os.path.join(directory, item['name']) for directory in sdk_directories
                       if entry(os.path.join(directory, item['name'])) is not None]
            require(len(matches) == 1, 'SDK library input is missing or ambiguous')
            source = matches[0]
            info = entry(source)
            require(info is not None and stat.S_ISLNK(info.st_mode), 'SDK library input must be a symbolic link')
            link = os.readlink(source)
            require(library_name(link), 'SDK library input requires a direct basename link')
            provider = os.path.join(os.path.dirname(source), link)
            provider_info = regular_file(provider)
            require(canonical_existing(provider) == provider and within(provider, sysroot),
                    'SDK library provider is not canonical')
            require(sha256_file(provider) == item['sha256'], 'SDK library input SHA256 differs')
            dynamic = read_elf_dynamic(provider, machine=machine)
            require(dynamic['type'] == 3 and library_name(dynamic['soname']),
                    'SDK library input requires ET_DYN and a safe SONAME')
            soname = dynamic['soname']
            require(soname not in files or files[soname] == provider, 'conflicting SDK library input SONAME')
            files[soname] = provider
            if provider not in pending:
                pending.append(provider)
            declared_libraries.append(dict(name=item['name'], sha256=item['sha256'], source=source,
                source_identity=stable_identity(info), source_link=link, provider=provider,
                provider_identity=stable_identity(provider_info), soname=soname))

        def verify_library_inputs():
            if library_root is not None:
                require(canonical_existing(sysroot) == sysroot and
                        stable_identity(real_directory(sysroot))[:3] == stable_identity(library_root)[:3],
                        'SDK library root identity changed')
            for item in declared_libraries:
                source, provider = item['source'], item['provider']
                info = entry(source)
                require(info is not None and stable_identity(info) == tuple(item['source_identity'])
                        and stat.S_ISLNK(info.st_mode) and os.readlink(source) == item['source_link']
                        and canonical_existing(os.path.dirname(source)) == os.path.dirname(source)
                        and canonical_existing(source) == provider, 'SDK library input identity changed')
                info = regular_file(provider)
                require(stable_identity(info) == tuple(item['provider_identity']) and
                        sha256_file(provider) == item['sha256'], 'SDK library provider changed')
        verify_library_inputs()
        declared_providers = {item['soname']: item['provider'] for item in declared_libraries}
        while pending:
            file = pending.pop(0)
            try:
                dynamic = read_elf_dynamic(file, machine=machine)
            except SDKError as error:
                raise QueryError(f'not little-endian {processor} ELF64: {file}: {error}') from error
            localdirs = []
            for value in (dynamic['rpath'], dynamic['runpath']):
                if value is not None:
                    localdirs.extend(mapdir(path.replace('${ORIGIN}', os.path.dirname(file)).replace('$ORIGIN', os.path.dirname(file)))
                                     for path in value.split(':'))
            for name in dynamic['needed']:
                require(re.fullmatch(r'[a-zA-Z0-9._+-]+', name), 'unsafe SONAME')
                candidate = next((os.path.join(directory, name) for directory in search + localdirs + defaults
                                  if os.path.isfile(os.path.join(directory, name))), None)
                require(candidate is not None, f'missing provider: {name}')
                candidate = canonical_existing(candidate)
                require(any(within(candidate, root) for root in roots), 'provider outside target/build roots')
                if name in declared_providers:
                    require(candidate == declared_providers[name],
                            f'declared SDK provider differs: {name}')
                if name in files:
                    require(sha256_file(candidate) == sha256_file(files[name]),
                            f'conflicting {name}: {files[name]} versus {candidate}')
                else:
                    files[name] = candidate
                    pending.append(candidate)

        aliases = [item for item in declared_libraries if item['name'] != item['soname']]
        require(all(item['name'] not in files for item in aliases), 'SDK library alias collides with a provider')
        sources = {path: sha256_file(path) for path in sorted({exe, *files.values(), *([in_path] if in_path else [])})}
        query_path = stage / query_relative
        query_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(exe, query_path)
        query_path.chmod(0o755)
        for name, path in files.items():
            shutil.copy(path, stage / 'lib' / name)
        for item in declared_libraries:
            require(sha256_file(stage / 'lib' / item['soname']) == item['sha256'],
                    'staged SDK library input SHA256 differs')
        if declared_libraries:
            write_json(work / 'library-inputs.json', dict(inputs=declared_libraries))
        if in_path:
            shutil.copy(in_path, stage / 'types.txt')
        for source, path, expected, info in artifacts:
            require(canonical_existing(source) == source, 'data source ancestors changed')
            handle, opened = open_regular(source)
            with handle:
                require(stable_identity(opened) == stable_identity(info), 'data source identity changed')
                payload = handle.read(info.st_size + 1)
                require(len(payload) == info.st_size, 'data source size changed while copying')
                require(stable_identity(os.fstat(handle.fileno())) == stable_identity(info),
                        'data source changed while copying')
                destination = stage / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as output:
                    output.write(payload)
            verify_stable(source, info)
            require(sha256_file(destination) == expected, 'staged data SHA256 differs')
            sources[source] = expected
        verify_data_roots()
        if artifacts or resource_env:
            write_json(work / 'data-inputs.json', dict(
                roots={root: stable_identity(info)[:3] for root, info in data_roots.items()},
                files=[dict(source=source, path=path, sha256=expected, identity=stable_identity(info))
                       for source, path, expected, info in artifacts], environment=resource_env))
        manifest = ''.join(f'{sha256_file(path)}  {path.relative_to(stage).as_posix()}\n'
                           for path in sorted(stage.rglob('*')) if path.is_file())
        manifest += ''.join(item['sha256'] + '  lib/' + item['name'] + '\n'
                            for item in sorted(aliases, key=lambda item: item['name']))
        (stage / 'files.sha256').write_text(manifest, encoding='utf-8')
        (work / 'files.sha256').write_text(manifest, encoding='utf-8')
        (work / 'sources.sha256').write_text(''.join(f'{digest}  {path}\n' for path, digest in sources.items()), encoding='utf-8')
        remote = None
        try:
            allocation = ('test "$(uname -s)" = NetBSD && test "$(uname -p)" = ' + processor
                          + ' && umask 077 && mktemp -d /tmp/ember-gir.XXXXXXXX')
            remote = run('allocate', ssh + [allocation]).decode('utf-8', 'strict').strip()
            require(REMOTE_DIRECTORY.fullmatch(remote), 'invalid temporary directory')
            # Reuse only byte-identical installed sysroot providers. In-tree
            # libraries always travel. Both manifests cover all reused bytes.
            reusable = {name: path for name, path in files.items() if within(path, sysroot)}
            if reusable:
                reuse_script = f'set -eu\ncd {shlex.quote(remote)}\nmkdir -p lib\n'
                for name, path in reusable.items():
                    installed, expected, copy = path.removeprefix(sysroot), sources[path], 'lib/' + name
                    reuse_script += (f'if test -f {shlex.quote(installed)} && test "$(sha256 -q {shlex.quote(installed)})" = {expected}; then\n'
                                     f'  cp {shlex.quote(installed)} {shlex.quote(copy)}\n'
                                     f'  test "$(sha256 -q {shlex.quote(copy)})" = {expected} || exit 92\n'
                                     f"  printf '%s\\n' {shlex.quote(name)}\nfi\n")
                (work / 'reuse.sh').write_text(reuse_script, encoding='utf-8')
                reused = run('reuse', ssh + ['sh -s -- ember-gir-reuse'], reuse_script.encode('utf-8')).decode('utf-8', 'strict').splitlines()
                require(len(set(reused)) == len(reused) and all(name in reusable for name in reused), 'invalid reused library response')
                for name in reused:
                    (stage / 'lib' / name).unlink()
            archive = work / 'input.tar.gz'
            with tarfile.open(archive, 'x:gz', format=tarfile.USTAR_FORMAT) as output:
                output.add(stage, arcname='.')
            (work / 'tar.log').write_bytes(b'')
            (work / 'transfer-size.txt').write_text(f'{archive.stat().st_size}\n', encoding='ascii')
            verify_library_inputs()
            run('transfer', ssh + [f'tar -xzf - -C {shlex.quote(remote)}'], archive.read_bytes(),
                timeout=transfer_timeout_seconds)
            invocation = [remote + '/' + query_relative]
            if execute:
                invocation.extend(args)
            if out_path:
                invocation.append(f'--introspect-dump={remote}/types.txt,{remote}/dump.xml')
            exports = ''.join('export ' + name + '=' + shlex.quote(
                value['literal'] if 'literal' in value else remote + '/' + value['stage_path']) + '\n'
                for name, value in sorted(resource_env.items()))
            alias_setup, alias_verify = '', ''
            for item in aliases:
                name, target = shlex.quote('lib/' + item['name']), shlex.quote(item['soname'])
                alias_setup += f'test ! -e {name}\ntest ! -L {name}\nln -s {target} {name}\n'
                alias_verify += f'test -L {name}\ntest "$(readlink {name})" = {target}\n'
            script = f'''set -eu
cd {shlex.quote(remote)}
{alias_setup}{alias_verify}while read hash name; do
  test "$(sha256 -q "$name")" = "$hash" || exit 90
done < files.sha256
ulimit -c 0
ulimit -f 16384
export LD_LIBRARY_PATH={shlex.quote(remote + '/lib')}
unset LD_PRELOAD
{exports}set +e
timeout -k 5 60 {shlex.join(invocation)} > stdout.log 2> stderr.log
result=$?
set -e
{alias_verify}while read hash name; do
  test "$(sha256 -q "$name")" = "$hash" || exit 91
done < files.sha256
cat stdout.log
cat stderr.log >&2
printf '%s\\n' "$result" > execution.status
exit "$result"
'''
            result = completed(ssh + ['sh -s'], script.encode('utf-8'))
            if execute:
                (work / 'target.log').write_bytes(result.stdout)
                (work / 'target-stderr.log').write_bytes(result.stderr)
                sys.stdout.buffer.write(result.stdout)
                sys.stderr.buffer.write(result.stderr)
            else:
                output = result.stdout + result.stderr
                (work / 'target.log').write_bytes(output)
                sys.stderr.buffer.write(output)
            target_status = result.returncode if result.returncode >= 0 else 1
            (work / 'exit.txt').write_text(f'{target_status}\n', encoding='ascii')
            if execute:
                receipt = run('execution-status', ssh + [f'cat {remote}/execution.status']).strip()
                require(receipt == str(target_status).encode('ascii'), 'target execution receipt differs from transport status')
            require(execute or result.returncode == 0, f'target query failed ({target_status}), {work}')
            if out_path:
                command = ssh + [f'test -s {remote}/dump.xml && cat {remote}/dump.xml']
                try:
                    xml_result = stream.capture_streamed(command, env=environment, stdout_limit=XML_LIMIT, timeout=180,
                                                         empty_snapshot_timeout=30)
                    xml, diagnostics, xml_status = xml_result.value, xml_result.stderr, 0
                    xml_truncated = xml_result.stderr_truncated
                except CommandError as error:
                    xml, diagnostics, xml_status = error.stdout, error.stderr, error.returncode
                    xml_truncated = error.stdout_truncated or error.stderr_truncated
                except ProcessOwnershipError:
                    raise
                except SDKError as error:
                    # capture_streamed drains and checks the producer before
                    # it reports overflow. It does not expose a completed
                    # result for this refusal, so do not invent an exit code.
                    (work / 'xml-transfer.log').write_text(
                        f'refused: {error}\nstdout_limit={XML_LIMIT}\n', encoding='utf-8')
                    raise QueryError('invalid introspection XML') from error
                (work / 'xml-transfer.log').write_bytes(f'exit={xml_status} bytes={len(xml)}\n'.encode('ascii') + diagnostics)
                if len(xml) <= XML_LIMIT:
                    (work / 'dump.xml').write_bytes(xml)
                require(xml_status == 0 and not xml_truncated and len(xml) <= XML_LIMIT and b'<dump' in xml,
                        'invalid introspection XML')
        finally:
            if remote is not None and REMOTE_DIRECTORY.fullmatch(remote):
                cleanup = completed(ssh + [f'rm -rf -- {shlex.quote(remote)}'])
                (work / 'cleanup.log').write_bytes(f'{cleanup.returncode}\n'.encode('ascii') + cleanup.stdout + cleanup.stderr)
                require(cleanup.returncode == 0, f'remote cleanup failed: {remote}')
        try:
            unchanged = all(sha256_file(path) == digest for path, digest in sources.items())
        except (OSError, SDKError):
            unchanged = False
        require(unchanged, 'source providers changed during query')
        verify_library_inputs()
        for source, unused_path, unused_hash, info in artifacts:
            require(canonical_existing(source) == source, 'data source ancestors changed during query')
            verify_stable(source, info)
        verify_data_roots()
        if out_path:
            fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as output:
                output.write(xml)
        shutil.rmtree(stage)
        archive.unlink()
        failure.complete = True
        return target_status if execute else 0


def main(arguments=None):
    try:
        require(sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 15),
                "use the selected build-host CPython 3.15")
        arguments = list(sys.argv[1:] if arguments is None else arguments)
        selection = []
        # SDK options belong before the query mode/program. Preserve every
        # later argument, including a literal target --sdk-source option.
        while arguments and arguments[0] == '--sdk-source':
            selection.extend(arguments[:2])
            del arguments[:2]
        unused_source, unused_options = load_sdk(selection)
        install_signal_handlers()
        return query(arguments)
    except (QueryError, OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        from emberbsd_sdk.errors import SDKError
        if not isinstance(error, SDKError):
            raise
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
