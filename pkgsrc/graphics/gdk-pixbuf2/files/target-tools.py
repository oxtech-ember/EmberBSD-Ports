#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Ported from target-tools.rb.
"""Run GdkPixbuf build tools against verified EmberBSD target modules."""

import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True

import pixbuf_data
from sdk_source import install_signal_handlers, load_sdk

TARGETS = {'aarch64': ('aarch64', 183), 'amd64': ('x86_64', 62)}
REMOTE_DIRECTORY = re.compile(r'/tmp/ember-pixbuf\.[A-Za-z0-9]{8}')
MODULE_LINE = re.compile(rb'^"(/[^"\n]+\.so)"$', re.MULTILINE)


class ToolError(Exception):
    """A pixbuf policy or transport check refused the query."""


def require(condition, message):
    if not condition:
        raise ToolError(message)


def query(arguments):
    from emberbsd_sdk.elf import read_elf_dynamic
    from emberbsd_sdk.errors import CommandError, SDKError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json
    from emberbsd_sdk import stream
    from emberbsd_sdk.paths import canonical_existing, real_directory, regular_file, relative_inside

    require(getattr(stream, 'PRODUCER_STREAM_API', None) == 1,
            'selected SDK lacks producer stream API 1')
    require(getattr(stream, 'PRODUCER_INPUT_API', None) == 1,
            'selected SDK lacks producer input API 1')
    require(getattr(stream, 'PRODUCER_INSPECTION_API', None) == 1,
            'selected SDK lacks producer inspection API 1')
    config = read_json(os.environ['EMBERBSD_GI_QUERY_CONFIG'])
    require(isinstance(config, dict), 'GI query configuration must be an object')
    target = config.get('target', 'aarch64')
    require(isinstance(target, str) and target in TARGETS, 'unsupported pixbuf target architecture')
    arch, machine = TARGETS[target]
    require('EMBERBSD_GI_TARGET' not in os.environ or os.environ['EMBERBSD_GI_TARGET'] == target,
            'configuration differs from recipe target architecture')

    def absolute(key):
        value = config[key]
        require(isinstance(value, str) and value.startswith('/'), f'{key} must be absolute')
        return canonical_existing(value)

    # Legacy config/--check retains the selected readelf identity. SDK API 1
    # reads ELF bytes directly and does not invoke the configured tool.
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
    host = config['ssh']
    require(isinstance(host, str) and re.fullmatch(r'(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*', host),
            'invalid SSH destination')
    command = 'ssh'
    if 'ssh_executable' in config:
        selected = config['ssh_executable']
        require(isinstance(selected, str) and os.path.isabs(selected), 'SSH executable must be absolute')
        command = canonical_existing(selected)
        regular_file(command)
        require(os.access(command, os.X_OK), 'SSH executable is not executable')
    ssh = [command, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'ConnectTimeout=5', '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3']
    if 'ssh_config' in config:
        selected = config['ssh_config']
        require(isinstance(selected, str) and os.path.isabs(selected), 'SSH config must be absolute')
        selected = canonical_existing(selected)
        regular_file(selected)
        ssh += ['-F', selected]
    if 'ssh_port' in config:
        port = config['ssh_port']
        require(type(port) is int and 1 <= port <= 65535, 'invalid SSH port')
        ssh += ['-p', str(port)]
    if 'host_key_alias' in config:
        alias = config['host_key_alias']
        require(isinstance(alias, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', alias),
                'invalid host key alias')
        ssh += ['-o', 'HostKeyAlias=' + alias]
    ssh.append(host)
    if arguments and arguments[0] == '--check':
        require(len(arguments) == 4, 'usage: --check WORKDIR SYSROOT READELF')
        workdir, target_root, tool = map(canonical_existing, arguments[1:])
        require(within(workdir, base) and target_root == sysroot and tool == readelf, 'configuration differs from recipe')
        print('PASS: GI query configuration matches the selected work, sysroot and readelf')
        return 0

    require(bool(arguments) and arguments[0] in ('--loaders', '--mime'),
            'usage: --loaders QUERY MODULE... | --mime PRINTER CACHE')
    mode, *arguments = arguments
    require(bool(arguments), 'binary required')
    exe, *arguments = arguments
    exe = canonical_existing(exe)
    require(within(exe, base), 'binary outside build root')
    expected = 'gdk-pixbuf-query-loaders' if mode == '--loaders' else 'gdk-pixbuf-print-mime-types'
    require(os.path.basename(exe) == expected, 'unexpected target tool')
    cache_input = cache_bytes = None
    if mode == '--loaders':
        modules = list(map(canonical_existing, arguments))
    else:
        require(len(arguments) == 1, 'one cache required')
        cache_input = canonical_existing(arguments[0])
        require(within(cache_input, base), 'cache outside build root')
        cache_bytes = Path(cache_input).read_bytes()
        cache_bytes.decode('utf-8', 'strict')
        modules = [canonical_existing(path.decode('utf-8', 'strict')) for path in MODULE_LINE.findall(cache_bytes)]
    require(bool(modules), 'missing target modules')
    require(len({os.path.basename(path) for path in modules}) == len(modules), 'duplicate target modules')
    for path in modules:
        require(within(path, base) and re.fullmatch(r'libpixbufloader-[a-z0-9]+\.so', os.path.basename(path)),
                'invalid target module')

    work = Path(tempfile.mkdtemp(prefix='pixbuf-tool-', dir=cache))
    stage = work / 'stage'
    (stage / 'lib').mkdir(parents=True)
    (stage / 'loaders').mkdir()
    environment = dict(os.environ)

    def completed(command, data=None):
        try:
            result = stream.capture_streamed(command, env=environment, input=data,
                                                timeout=180, stdout_limit=16 * 1024 * 1024,
                                            empty_snapshot_timeout=30)
            require(not result.stderr_truncated, 'host command stderr exceeds capture limit')
            return subprocess.CompletedProcess(command, 0, result.value, result.stderr)
        except CommandError as error:
            require(not error.stdout_truncated and not error.stderr_truncated,
                    'host command output exceeds capture limit')
            return subprocess.CompletedProcess(command, error.returncode, error.stdout, error.stderr)

    def run(name, command, data=None):
        result = completed(command, data)
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
    candidates = [os.path.dirname(path) for path in modules] + configured + environment.get('LD_LIBRARY_PATH', '').split(':')
    search = list(dict.fromkeys(mapdir(path) for path in candidates if path))
    defaults = [mapdir(path) for path in ('/usr/pkg/gcc16/lib', '/usr/pkg/lib', '/usr/lib', '/lib')]
    files, pending = {}, [exe, *modules]
    while pending:
        file = pending.pop(0)
        try:
            dynamic = read_elf_dynamic(file, machine=machine)
        except SDKError as error:
            raise ToolError(f'not little-endian {arch} ELF64: {file}: {error}') from error
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
            if name in files:
                require(sha256_file(candidate) == sha256_file(files[name]),
                        f'conflicting {name}: {files[name]} versus {candidate}')
            else:
                files[name] = candidate
                pending.append(candidate)

    inputs = {exe, *files.values(), *modules, *([cache_input] if cache_input else [])}
    sources = {path: sha256_file(path) for path in sorted(inputs)}
    shutil.copy(exe, stage / 'query')
    (stage / 'query').chmod(0o755)
    for name, path in files.items():
        shutil.copy(path, stage / 'lib' / name)
    for path in modules:
        shutil.copy(path, stage / 'loaders' / os.path.basename(path))
    manifest = ''.join(f'{sha256_file(path)}  {path.relative_to(stage).as_posix()}\n'
                       for path in sorted(stage.rglob('*')) if path.is_file())
    (stage / 'files.sha256').write_text(manifest, encoding='utf-8')
    (work / 'files.sha256').write_text(manifest, encoding='utf-8')
    (work / 'sources.sha256').write_text(''.join(f'{digest}  {path}\n' for path, digest in sources.items()), encoding='utf-8')
    archive = work / 'input.tar.gz'
    with tarfile.open(archive, 'x:gz', format=tarfile.USTAR_FORMAT) as output:
        output.add(stage, arcname='.')
    (work / 'tar.log').write_bytes(b'')
    remote = None
    try:
        allocation = ('test "$(uname -s)" = NetBSD && test "$(uname -p)" = ' + arch
                      + ' && umask 077 && mktemp -d /tmp/ember-pixbuf.XXXXXXXX')
        remote = run('allocate', ssh + [allocation]).decode('utf-8', 'strict').strip()
        require(REMOTE_DIRECTORY.fullmatch(remote), 'invalid temporary directory')
        run('transfer', ssh + [f'tar -xzf - -C {shlex.quote(remote)}'], archive.read_bytes())
        invocation = [remote + '/query']
        if mode == '--loaders':
            invocation.extend(remote + '/loaders/' + os.path.basename(path) for path in modules)
        else:
            target_cache = Path(cache_input).read_bytes()
            for path in modules:
                target_cache = target_cache.replace(path.encode('utf-8'), (remote + '/loaders/' + os.path.basename(path)).encode('utf-8'))
            digest = hashlib.sha256(target_cache).hexdigest()
            (work / 'mime-cache.sha256').write_text(digest + '  loaders.cache\n', encoding='ascii')
            run('cache', ssh + [f"cat > {remote}/loaders.cache && printf '%s\\n' '{digest}  loaders.cache' >> {remote}/files.sha256"], target_cache)
        script = f'''set -eu
cd {shlex.quote(remote)}
while read hash name; do
  test "$(sha256 -q "$name")" = "$hash" || exit 90
done < files.sha256
ulimit -c 0
ulimit -f 16384
export LD_LIBRARY_PATH={shlex.quote(remote + '/lib')}
export GDK_PIXBUF_MODULE_FILE={shlex.quote(remote + '/loaders.cache')}
unset LD_PRELOAD
set +e
timeout -k 5 60 {shlex.join(invocation)} > stdout.log 2> stderr.log
result=$?
set -e
while read hash name; do
  test "$(sha256 -q "$name")" = "$hash" || exit 91
done < files.sha256
cat stdout.log
cat stderr.log >&2
exit "$result"
'''
        result = completed(ssh + ['sh -s'], script.encode('utf-8'))
        output = result.stdout
        output.decode('utf-8', 'strict')
        (work / 'target.log').write_bytes(output)
        (work / 'target.stderr').write_bytes(result.stderr)
        (work / 'exit.txt').write_text(f'{result.returncode}\n', encoding='ascii')
        sys.stderr.buffer.write(result.stderr)
        require(result.returncode == 0, f'target query failed ({result.returncode}), {work}')
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
    if mode == '--loaders':
        for path in modules:
            output = output.replace((remote + '/loaders/' + os.path.basename(path)).encode('utf-8'), path.encode('utf-8'))
        require(remote.encode('ascii') not in output, 'query output contains remote path')
        require(sorted(MODULE_LINE.findall(output)) == sorted(path.encode('utf-8') for path in modules), 'incomplete loader query')
    else:
        require(re.fullmatch(rb'[a-zA-Z0-9.+_-]+/[a-zA-Z0-9.+_-]+;(?:[a-zA-Z0-9.+_-]+/[a-zA-Z0-9.+_-]+;)*', output),
                'invalid MIME query output')
    shutil.rmtree(stage)
    archive.unlink()
    return output


def main(arguments=None):
    try:
        require(sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 15),
                "use the selected build-host CPython 3.15")
        arguments = list(sys.argv[1:] if arguments is None else arguments)
        selection = []
        while arguments and arguments[0] == '--sdk-source':
            selection.extend(arguments[:2])
            del arguments[:2]
        data_mode = pixbuf_data.mode(os.environ)
        kind = arguments[0][2:] if arguments and arguments[0] in ('--loaders', '--mime') else None
        if kind is not None:
            require(len(arguments) >= 2, 'binary required')
            expected = 'gdk-pixbuf-query-loaders' if kind == 'loaders' else 'gdk-pixbuf-print-mime-types'
            require(os.path.basename(arguments[1]) == expected, 'unexpected target tool')
            # The paths a live query reports: canonical existing files.
            inputs = [os.path.realpath(path) for path in arguments[2:]]
            for path in inputs:
                require(os.path.isfile(path), f'missing input: {path}')
        if kind is not None and data_mode == 'replay':
            # Stored target data: no SDK, no target and no query configuration.
            sys.stdout.buffer.write(pixbuf_data.replay(os.environ, kind, inputs))
            return 0
        unused_source, unused_options = load_sdk(selection)
        install_signal_handlers()
        output = query(arguments)
        if kind is None:
            return output
        if data_mode == 'capture':
            stored = pixbuf_data.capture(os.environ, kind, inputs, output)
            print(f'Stored GdkPixbuf target data: {stored}', file=sys.stderr)
        sys.stdout.buffer.write(output)
        return 0
    except (ToolError, pixbuf_data.DataError, OSError, ValueError, KeyError) as error:
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
