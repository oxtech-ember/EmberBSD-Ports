#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), ported from the EmberBSD Ruby target-tool runner.
"""Run GdkPixbuf loader and MIME queries with verified target providers."""
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile


class QueryError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise QueryError(message)


def bind_sdk():
    require(sys.version_info[:2] == (3, 15), 'Use the qualified native Python 3.15 interpreter.')
    selected = os.environ.get('EMBERBSD_SDK_SOURCE')
    require(isinstance(selected, str) and selected.startswith('/'), 'SDK source must be an explicit absolute path')
    require((Path(selected) / 'src/emberbsd_sdk/__init__.py').is_file(), 'SDK source must exist and provide host API 1')
    source = Path(selected).resolve(strict=True)
    sys.path.insert(0, str(source / 'src'))
    import emberbsd_sdk
    require(emberbsd_sdk.API_VERSION == 1 and
            Path(emberbsd_sdk.__file__).resolve().parent == source / 'src/emberbsd_sdk',
            'The selected SDK source must provide host API 1.')
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json
    return sha256_file, read_json


def inside(path, root):
    return path == root or path.startswith(root + '/')


def canonical(value):
    return str(Path(value).resolve(strict=True))


def capture(command, *, data=None, merged=True):
    try:
        return subprocess.run(command, input=data, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT if merged else subprocess.PIPE,
                              timeout=180, check=False)
    except subprocess.TimeoutExpired as error:
        raise QueryError('host command timed out: ' + command[0]) from error


def status_of(result):
    return result.returncode if result.returncode >= 0 else 1


def main(args):
    digest, read_json = bind_sdk()
    config = read_json(os.environ['EMBERBSD_GI_QUERY_CONFIG'])
    targets = {'aarch64': ('aarch64', 'AArch64'), 'amd64': ('x86_64', 'Advanced Micro Devices X86-64')}
    target = config.get('target', 'aarch64')
    require(target in targets, 'unsupported pixbuf target architecture')
    processor, machine = targets[target]
    require(os.environ.get('EMBERBSD_GI_TARGET', target) == target,
            'configuration differs from recipe target architecture')
    def absolute(key):
        value = config[key]
        require(isinstance(value, str) and value.startswith('/'), key + ' must be absolute')
        return canonical(value)
    base, sysroot, cache, readelf = map(absolute, ('build_root', 'sysroot', 'cache', 'readelf'))
    require(os.path.isfile(readelf) and os.access(readelf, os.X_OK), 'readelf is not executable')
    roots = (base, sysroot)
    require(not inside(base, sysroot) and not inside(sysroot, base), 'build/sysroot overlap')
    require(not inside(cache, sysroot) and not inside(sysroot, cache), 'cache overlaps providers')
    host = config['ssh']
    require(isinstance(host, str) and re.fullmatch(
        r'(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*', host), 'invalid SSH destination')
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
           '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3']
    if 'host_key_alias' in config:
        alias = config['host_key_alias']
        require(isinstance(alias, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', alias),
                'invalid host key alias')
        ssh += ['-o', 'HostKeyAlias=' + alias]
    ssh.append(host)
    if args and args[0] == '--check':
        require(len(args) == 4, 'usage: --check WORKDIR SYSROOT READELF')
        workdir, target_root, tool = map(canonical, args[1:])
        require(inside(workdir, base) and target_root == sysroot and tool == readelf,
                'configuration differs from recipe')
        print('PASS: GI query configuration matches the selected work, sysroot and readelf')
        return 0
    require(bool(args) and args[0] in ('--loaders', '--mime'),
            'usage: --loaders QUERY MODULE... | --mime PRINTER CACHE')
    mode, *args = args
    require(bool(args), 'binary required')
    exe = canonical(args[0])
    arguments = args[1:]
    require(inside(exe, base), 'binary outside build root')
    expected = 'gdk-pixbuf-query-loaders' if mode == '--loaders' else 'gdk-pixbuf-print-mime-types'
    require(os.path.basename(exe) == expected, 'unexpected target tool')
    cache_input = None
    if mode == '--loaders':
        modules = list(map(canonical, arguments))
    else:
        require(len(arguments) == 1, 'one cache required')
        cache_input = canonical(arguments[0])
        require(inside(cache_input, base), 'cache outside build root')
        modules = [canonical(path) for path in re.findall(r'^"(/[^"\n]+\.so)"$', Path(cache_input).read_text(encoding='utf-8'), re.M)]
    require(modules, 'missing target modules')
    require(len({os.path.basename(path) for path in modules}) == len(modules), 'duplicate target modules')
    for path in modules:
        require(inside(path, base) and re.fullmatch(r'libpixbufloader-[a-z0-9]+\.so', os.path.basename(path)),
                'invalid target module')
    work = Path(tempfile.mkdtemp(prefix='pixbuf-tool-', dir=cache))
    stage = work / 'stage'
    for name in ['lib', 'loaders']:
        (stage / name).mkdir(parents=True)
    def run(name, *command, data=None):
        result = capture(list(command), data=data)
        (work / (name + '.log')).write_bytes(result.stdout)
        require(result.returncode == 0, f'{name} failed ({status_of(result)}); see {work}')
        return result.stdout
    def mapdir(path):
        if os.path.isdir(path):
            resolved = canonical(path)
            if any(inside(resolved, root) for root in roots):
                return resolved
        if any(inside(path, root) for root in roots):
            return path
        return sysroot + path if path.startswith('/') else os.path.abspath(path)
    extra = config.get('library_dirs', [])
    require(isinstance(extra, list) and all(isinstance(path, str) for path in extra), 'invalid library directories')
    search = [os.path.dirname(path) for path in modules] + extra + os.environ.get('LD_LIBRARY_PATH', '').split(':')
    search = list(dict.fromkeys(mapdir(path) for path in search if path))
    defaults = [mapdir(path) for path in ('/usr/pkg/gcc16/lib', '/usr/pkg/lib', '/usr/lib', '/lib')]
    files, pending = {}, [exe, *modules]
    while pending:
        file = pending.pop(0)
        result = capture([readelf, '-h', file])
        header = result.stdout.decode('utf-8', 'replace')
        actual = re.search(r'^\s*Machine:\s*(.*?)\s*$', header, re.M)
        require(result.returncode == 0 and actual and actual[1] == machine and
                re.search(r'Class:.*ELF64', header) and re.search(r'Data:.*little endian', header),
                f'not little-endian {processor} ELF64: {file}')
        result = capture([readelf, '-d', file])
        require(result.returncode == 0, 'readelf failed')
        dynamic = result.stdout.decode('utf-8', 'replace')
        localdirs = [mapdir(path.replace('${ORIGIN}', os.path.dirname(file)).replace('$ORIGIN', os.path.dirname(file)))
                     for paths in re.findall(r'\((?:RPATH|RUNPATH)\).*\[(.*?)\]', dynamic) for path in paths.split(':')]
        for name in re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic):
            require(re.fullmatch(r'[a-zA-Z0-9._+-]+', name), 'unsafe SONAME')
            candidate = next((directory + '/' + name for directory in search + localdirs + defaults
                              if os.path.isfile(directory + '/' + name)), None)
            require(candidate is not None, 'missing provider: ' + name)
            candidate = canonical(candidate)
            require(any(inside(candidate, root) for root in roots), 'provider outside target/build roots')
            if name in files:
                require(digest(candidate) == digest(files[name]),
                        f'conflicting {name}: {files[name]} versus {candidate}')
            else:
                files[name] = candidate
                pending.append(candidate)
    sources = {path: digest(path) for path in sorted({exe, *files.values(), *modules, *([cache_input] if cache_input else [])})}
    shutil.copyfile(exe, stage / 'query')
    (stage / 'query').chmod(0o755)
    for name, path in files.items():
        shutil.copyfile(path, stage / 'lib' / name)
    for path in modules:
        shutil.copyfile(path, stage / 'loaders' / os.path.basename(path))
    entries = sorted(path for path in stage.rglob('*') if path.is_file())
    manifest = ''.join(f'{digest(path)}  {path.relative_to(stage)}\n' for path in entries)
    (stage / 'files.sha256').write_text(manifest, encoding='utf-8')
    (work / 'files.sha256').write_text(manifest, encoding='utf-8')
    (work / 'sources.sha256').write_text(''.join(f'{value}  {path}\n' for path, value in sources.items()), encoding='utf-8')
    archive = work / 'input.tar.gz'
    run('tar', '/usr/bin/env', 'COPYFILE_DISABLE=1', 'tar', '--format=ustar', '--no-xattrs', '-czf', str(archive), '-C', str(stage), '.')
    remote = None
    try:
        remote = run('allocate', *ssh, 'test "$(uname -s)" = NetBSD && test "$(uname -p)" = ' + shlex.quote(processor) +
                     ' && umask 077 && mktemp -d /tmp/ember-pixbuf.XXXXXXXX').decode().strip()
        require(re.fullmatch(r'/tmp/ember-pixbuf\.[A-Za-z0-9]{8}', remote), 'invalid temporary directory')
        run('transfer', *ssh, 'tar -xzf - -C ' + shlex.quote(remote), data=archive.read_bytes())
        invocation = [remote + '/query']
        if mode == '--loaders':
            invocation += [remote + '/loaders/' + os.path.basename(path) for path in modules]
        else:
            target_cache = Path(cache_input).read_text(encoding='utf-8')
            for path in modules:
                target_cache = target_cache.replace(path, remote + '/loaders/' + os.path.basename(path))
            data = target_cache.encode()
            import hashlib
            value = hashlib.sha256(data).hexdigest()
            (work / 'mime-cache.sha256').write_text(value + '  loaders.cache\n', encoding='ascii')
            run('cache', *ssh, f"cat > {remote}/loaders.cache && printf '%s\\n' '{value}  loaders.cache' >> {remote}/files.sha256", data=data)
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
        result = capture([*ssh, 'sh -s'], data=script.encode(), merged=False)
        output = result.stdout
        (work / 'target.log').write_bytes(output)
        (work / 'target.stderr').write_bytes(result.stderr)
        (work / 'exit.txt').write_text(str(status_of(result)) + '\n', encoding='ascii')
        sys.stderr.buffer.write(result.stderr)
        require(result.returncode == 0, f'target query failed ({status_of(result)}), {work}')
    finally:
        if remote and re.fullmatch(r'/tmp/ember-pixbuf\.[A-Za-z0-9]{8}', remote):
            result = capture([*ssh, 'rm -rf -- ' + shlex.quote(remote)])
            (work / 'cleanup.log').write_bytes(str(status_of(result)).encode() + b'\n' + result.stdout)
            require(result.returncode == 0, 'remote cleanup failed: ' + remote)
    require(all(digest(path) == expected for path, expected in sources.items()), 'source providers changed during query')
    text = output.decode('utf-8', 'strict')
    if mode == '--loaders':
        for path in modules:
            text = text.replace(remote + '/loaders/' + os.path.basename(path), path)
        require(remote not in text, 'query output contains remote path')
        require(sorted(re.findall(r'^"(/[^"\n]+\.so)"$', text, re.M)) == sorted(modules), 'incomplete loader query')
    else:
        require(re.fullmatch(r'[a-zA-Z0-9.+_-]+/[a-zA-Z0-9.+_-]+;(?:[a-zA-Z0-9.+_-]+/[a-zA-Z0-9.+_-]+;)*', text),
                'invalid MIME query output')
    sys.stdout.buffer.write(text.encode())
    shutil.rmtree(stage)
    archive.unlink()
    return 0


def terminated(signum, _frame):
    raise SystemExit(128 + signum)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, terminated)
    try:
        sys.exit(main(sys.argv[1:]))
    except (QueryError, OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(str(error))
    except Exception as error:
        if error.__class__.__module__.startswith('emberbsd_sdk.'):
            sys.exit(str(error))
        raise
