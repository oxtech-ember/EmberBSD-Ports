#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), ported from the scoped Ruby guards.
"""Use GCC16 ELF and mocked SSH to check loader/MIME transport, not target execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys

sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    from emberbsd_sdk.inventory import sha256_file
    return sha256_file(str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', default=os.environ.get('EMBERBSD_SDK_SOURCE'), type=Path)
    parser.add_argument('--helper', type=Path)
    for name in ['source', 'python', 'sysroot', 'readelf', 'new_work']:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    require(sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15),
            'use the selected build-host CPython 3.15')
    require(args.sdk_source is not None and args.sdk_source.is_absolute(),
            'set an absolute --sdk-source or EMBERBSD_SDK_SOURCE')
    source, python, sysroot, readelf, sdk = [path.resolve(strict=True) for path in
        [args.source, args.python, args.sysroot, args.readelf, args.sdk_source]]
    require(python == Path(sys.executable).resolve(strict=True), 'HOST_PYTHON must be the selected sys.executable')
    sys.path.insert(0, str(sdk / 'src'))
    import emberbsd_sdk
    require(type(emberbsd_sdk.API_VERSION) is int and emberbsd_sdk.API_VERSION == 1 and
            Path(emberbsd_sdk.__file__).resolve().parent == sdk / 'src/emberbsd_sdk',
            'the selected SDK must provide API version 1')
    processor = os.environ.get('EMBERBSD_CROSS_ARCH', 'aarch64')
    require(processor in ('aarch64', 'x86_64'), 'unsupported target architecture')
    target = 'amd64' if processor == 'x86_64' else 'aarch64'
    require(args.new_work.is_absolute() and not os.path.lexists(args.new_work), 'new absolute work required')
    work = args.new_work
    for directory in ['build/provider', 'build/other', 'cache', 'bin', 'outside', 'tmp']:
        (work / directory).mkdir(mode=0o700, parents=True, exist_ok=True)
    helper = (args.helper or Path(__file__).resolve().parent.parent /
              '../../pkgsrc/graphics/gdk-pixbuf2/files/target-tools.py').resolve(strict=True)
    cc = readelf.with_name(readelf.name.removesuffix('readelf') + 'gcc')
    require(cc.is_file(), 'matching cross GCC driver missing')
    env = dict(os.environ, EMBERBSD_SDK_SOURCE=str(sdk), EMBERBSD_GI_TARGET=target,
               PATH=str(work / 'bin') + ':/usr/bin:/bin', TMPDIR=str(work / 'tmp'), TMP=str(work / 'tmp'),
               TEMP=str(work / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
    for name in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'DYLD_LIBRARY_PATH'):
        env.pop(name, None)
    receipts = []
    def capture(name, command, *, changes=None, data=None):
        selected = dict(env)
        for key, value in (changes or {}).items():
            if value is None:
                selected.pop(key, None)
            else:
                selected[key] = value
        result = subprocess.run(list(map(str, command)), env=selected, input=data, capture_output=True, timeout=180)
        (work / (name + '.stdout')).write_bytes(result.stdout)
        (work / (name + '.stderr')).write_bytes(result.stderr)
        receipts.append(dict(name=name, status=result.returncode, argv=list(map(str, command))))
        return result
    version = capture('compiler-version', [cc, '--version'])
    require(version.returncode == 0 and re.search(rb'\b16\.\d', version.stdout), 'use the common GCC16 cross compiler')
    require(capture('python-version', [python, '--version']).stdout.startswith(b'Python 3.15.'), 'use native Python 3.15')
    (work / 'build/provider.c').write_text('int pixbuf_guard_provider(void) { return 42; }\n')
    (work / 'build/query.c').write_text('extern int pixbuf_guard_provider(void); void _start(void) { (void)pixbuf_guard_provider(); }\n')
    provider = work / 'build/provider/libpixbuf-guard.so.1'
    require(capture('provider', [cc, '-nostdlib', '-shared', '-fPIC', work / 'build/provider.c',
        '-Wl,-soname,libpixbuf-guard.so.1', '-o', provider]).returncode == 0, 'provider link failed')
    query = work / 'build/gdk-pixbuf-query-loaders'
    printer = work / 'build/gdk-pixbuf-print-mime-types'
    module = work / 'build/libpixbufloader-bmp.so'
    for name, output, flags in [('query', query, ['-Wl,-e,_start']), ('printer', printer, ['-Wl,-e,_start']),
                                ('module', module, ['-shared', '-fPIC'])]:
        require(capture('link-' + name, [cc, '-nostdlib', *flags, work / 'build/query.c',
            '-L' + str(provider.parent), '-Wl,-l:libpixbuf-guard.so.1', '-Wl,-rpath,$ORIGIN/provider', '-o', output]).returncode == 0,
            name + ' link failed')
    (work / 'provider-alias').symlink_to(provider.parent)
    config = dict(target=target, build_root=str(work / 'build'), cache=str(work / 'cache'), sysroot=str(sysroot),
                  readelf=str(readelf), ssh='unused.invalid', host_key_alias='target.example',
                  library_dirs=[str(work / 'provider-alias')])
    config_path = work / 'query.json'
    env['EMBERBSD_GI_QUERY_CONFIG'] = str(config_path)
    def save_config(value):
        config_path.write_text(json.dumps(value) + '\n')
    save_config(config)
    marker = work / 'ssh-reached'
    ssh = work / 'bin/ssh'
    ssh.write_text('#!/bin/sh\nprintf unexpected-transport >> ' + shlex.quote(str(marker)) + '\nexit 97\n')
    ssh.chmod(0o755)
    def reject(name, reason, *arguments, changes=None):
        marker.unlink(missing_ok=True)
        result = capture(name, [python, '-E', '-S', helper, *arguments], changes=changes)
        require(result.returncode != 0 and reason.encode() in result.stderr and not marker.exists() and not result.stdout,
                name + ': expected local refusal: ' + result.stderr.decode(errors='replace'))
    for name, value, reason in [
        ('sdk-missing', None, 'Use --sdk-source or EMBERBSD_SDK_SOURCE with an absolute SDK source'),
        ('sdk-relative', os.path.relpath(sdk), 'Use --sdk-source or EMBERBSD_SDK_SOURCE with an absolute SDK source'),
        ('sdk-absent-directory', str(work / 'missing-sdk'), 'missing-sdk')]:
        reject(name, reason, '--check', work / 'build', sysroot, readelf,
               changes={'EMBERBSD_SDK_SOURCE': value})
    foreign_sdk = work / 'foreign-sdk/src/emberbsd_sdk'
    foreign_sdk.mkdir(parents=True)
    (foreign_sdk / '__init__.py').write_text('API_VERSION=99\n')
    reject('sdk-foreign-api', 'The selected SDK must provide API version 1',
           '--check', work / 'build', sysroot, readelf,
           changes={'EMBERBSD_SDK_SOURCE': str(work / 'foreign-sdk')})
    result = capture('sdk-preflight', [python, '-E', '-S', helper, '--check', work / 'build', sysroot, readelf])
    require(result.returncode == 0 and not marker.exists(), 'SDK preflight reached transport or failed')
    cases = [('unknown-mode', 'usage:', '--other', query), ('no-modules', 'missing target modules', '--loaders', query),
             ('duplicate-modules', 'duplicate target modules', '--loaders', query, module, module),
             ('outside-binary', 'binary outside build root', '--loaders', '/usr/bin/true', module),
             ('outside-module', 'invalid target module', '--loaders', query, '/usr/bin/true'),
             ('wrong-tool', 'unexpected target tool', '--loaders', printer, module)]
    for name, reason, *arguments in cases:
        reject(name, reason, *arguments)
    original = module.read_bytes()
    shutil.copyfile('/usr/bin/true', module)
    reject('wrong-architecture', 'not little-endian ' + processor + ' ELF64', '--loaders', query, module)
    module.write_bytes(original)
    for label, offset, value in [('wrong-class', 4, 1), ('wrong-endian', 5, 2),
                                 ('wrong-machine', 18, 62 if processor == 'aarch64' else 183)]:
        changed = bytearray(original)
        if offset == 18:
            struct.pack_into('<H', changed, offset, value)
        else:
            changed[offset] = value
        module.write_bytes(changed)
        reject(label, 'not little-endian ' + processor + ' ELF64', '--loaders', query, module)
    module.write_bytes(original)
    save_config(config | {'host_key_alias': 'bad alias'})
    reject('bad-alias', 'invalid host key alias', '--loaders', query, module)
    save_config(config | {'sysroot': str(work / 'build')})
    reject('overlap', 'build/sysroot overlap', '--loaders', query, module)
    save_config(config)
    config_path.write_text(json.dumps(config)[:-1] + ',"target":"aarch64"}\n')
    reject('duplicate-json', 'duplicate metadata key: target', '--loaders', query, module)
    save_config(config)
    cache_input = work / 'build/loaders.cache'
    cache_input.write_text('"' + str(module) + '"\n')
    reject('mime-no-cache', 'one cache required', '--mime', printer)
    reject('mime-outside-cache', 'cache outside build root', '--mime', printer, source / 'build-aux/gen-thumbnailer.py')
    cache_input.write_text('')
    reject('mime-no-modules', 'missing target modules', '--mime', printer, cache_input)
    cache_input.write_text(('"' + str(module) + '"\n') * 2)
    reject('mime-duplicate', 'duplicate target modules', '--mime', printer, cache_input)
    cache_input.write_text('"' + str(module) + '"\n')
    # A selected symlink cannot turn a host provider into a target provider.
    provider_data = provider.read_bytes()
    outside = work / 'outside/libpixbuf-guard.so.1'
    outside.write_bytes(provider_data)
    provider.unlink(); provider.symlink_to(outside)
    reject('escaping-provider', 'provider outside target/build roots', '--loaders', query, module)
    provider.unlink(); provider.write_bytes(provider_data)
    # Real selected providers with the same SONAME but different bytes conflict.
    other = work / 'build/other/libpixbuf-guard.so.1'
    other.write_bytes(provider_data + b'changed')
    require(capture('link-conflict', [cc, '-nostdlib', '-shared', '-fPIC', work / 'build/query.c',
        '-L' + str(provider.parent), '-Wl,-l:libpixbuf-guard.so.1', '-Wl,-rpath,$ORIGIN/other', '-o', module]).returncode == 0,
        'conflict fixture link failed')
    save_config(config | {'library_dirs': []})
    reject('conflicting-provider', 'conflicting libpixbuf-guard.so.1', '--loaders', query, module)
    module.write_bytes(original); save_config(config)
    # Transport injection never executes the target ELF images.
    ssh.write_text('#!' + str(python) + '\n' + r'''
import hashlib,io,json,os,sys,tarfile
from pathlib import Path
root=Path(os.environ['PIXBUF_GUARD_WORK']); scenario=os.environ['PIXBUF_GUARD_CASE']; command=sys.argv[-1]
if command.startswith('test '): phase='allocate'
elif command.startswith('tar '): phase='transfer'
elif command.startswith('cat > '): phase='cache'
elif command=='sh -s': phase='query'
elif command.startswith('rm -rf'): phase='cleanup'
else: raise SystemExit('unexpected mock SSH command')
with (root/(scenario+'.phases')).open('a') as f:f.write(phase+'\n')
(root/(scenario+'.ssh.json')).write_text(json.dumps(sys.argv[1:]))
if phase in ('transfer','cache','query'):
 data=sys.stdin.buffer.read();(root/(scenario+'.'+phase)).write_bytes(data)
if scenario==phase+'-failure': raise SystemExit(7)
if phase=='allocate':
 print('/tmp/ember-pixbuf.AbCd1234' if scenario!='bad-remote' else '/tmp/not-owned')
elif phase=='transfer':
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
  expected={}
  for line in archive.extractfile('./files.sha256').read().decode().splitlines():
   h,name=line.split('  ',1); expected[name]=h
  for name,h in expected.items():
   assert hashlib.sha256(archive.extractfile('./'+name).read()).hexdigest()==h
  assert {'query','lib/libpixbuf-guard.so.1','loaders/libpixbufloader-bmp.so'}<=set(expected)
elif phase=='query':
 if scenario=='input-change':
  p=Path(os.environ['PIXBUF_GUARD_MODULE']);p.write_bytes(p.read_bytes()+b'changed')
 if os.environ['PIXBUF_GUARD_MODE']=='--mime':
  print('image/png;image/bmp;' if scenario!='bad-mime' else 'not-a-mime',end='')
 elif scenario=='incomplete-loader': print('missing')
 elif scenario=='remote-leak': print('/tmp/ember-pixbuf.AbCd1234/unexpected')
 else: print('"/tmp/ember-pixbuf.AbCd1234/loaders/libpixbufloader-bmp.so"')
''')
    ssh.chmod(0o755)
    transport = [('loader-success', '--loaders', None, ['allocate', 'transfer', 'query', 'cleanup']),
                 ('mime-success', '--mime', None, ['allocate', 'transfer', 'cache', 'query', 'cleanup']),
                 ('allocate-failure', '--loaders', 'allocate failed', ['allocate']),
                 ('bad-remote', '--loaders', 'invalid temporary directory', ['allocate']),
                 ('transfer-failure', '--loaders', 'transfer failed', ['allocate', 'transfer', 'cleanup']),
                 ('cache-failure', '--mime', 'cache failed', ['allocate', 'transfer', 'cache', 'cleanup']),
                 ('query-failure', '--loaders', 'target query failed', ['allocate', 'transfer', 'query', 'cleanup']),
                 ('cleanup-failure', '--loaders', 'remote cleanup failed', ['allocate', 'transfer', 'query', 'cleanup']),
                 ('input-change', '--loaders', 'source providers changed', ['allocate', 'transfer', 'query', 'cleanup']),
                 ('incomplete-loader', '--loaders', 'incomplete loader query', ['allocate', 'transfer', 'query', 'cleanup']),
                 ('remote-leak', '--loaders', 'query output contains remote path', ['allocate', 'transfer', 'query', 'cleanup']),
                 ('bad-mime', '--mime', 'invalid MIME query output', ['allocate', 'transfer', 'cache', 'query', 'cleanup'])]
    for name, mode, reason, phases in transport:
        result = capture(name, [python, '-E', '-S', helper, mode, query if mode == '--loaders' else printer,
            module if mode == '--loaders' else cache_input], changes={'PIXBUF_GUARD_WORK':str(work),
            'PIXBUF_GUARD_CASE':name,'PIXBUF_GUARD_MODE':mode,'PIXBUF_GUARD_MODULE':str(module)})
        require((work / (name + '.phases')).read_text().splitlines() == phases, name + ': wrong cleanup phases')
        arguments = json.loads((work / (name + '.ssh.json')).read_text())
        for option in ['BatchMode=yes', 'StrictHostKeyChecking=yes', 'HostKeyAlias=target.example']:
            require(option in arguments, name + ': missing SSH identity option')
        if reason:
            require(result.returncode != 0 and not result.stdout and reason.encode() in result.stderr,
                    name + ': invalid failure publication')
        else:
            expected = ('"' + str(module) + '"\n').encode() if mode == '--loaders' else b'image/png;image/bmp;'
            require(result.returncode == 0 and result.stdout == expected, name + ': output contract differs')
            if mode == '--mime':
                mapped = (work / (name + '.cache')).read_bytes()
                require(str(module).encode() not in mapped and b'/tmp/ember-pixbuf.AbCd1234/loaders/libpixbufloader-bmp.so' in mapped,
                        'MIME cache paths were not rewritten')
                value=hashlib.sha256(mapped).hexdigest()
                require(any((entry/'mime-cache.sha256').exists() and (entry/'mime-cache.sha256').read_text().startswith(value)
                            for entry in (work/'cache').iterdir()), 'MIME cache hash receipt missing')
        module.write_bytes(original)
    # Run the production shell hash checks with a native timeout stub.
    # The cross ELF files are inspected and hashed; they are never executed.
    failing = next(entry for entry in (work / 'cache').iterdir()
                   if (entry / 'exit.txt').exists() and (entry / 'exit.txt').read_text() == '7\n')
    production = (work / 'query-failure.query').read_text()
    require(production.count('sha256 -q') == 2 and 'timeout -k 5 60 ' in production,
            'production pre/post hash or timeout guard missing')
    sha_tool = work / 'bin/sha256'
    sha_tool.write_text('#!' + str(python) + '\nimport hashlib,sys\n'
                        'with open(sys.argv[2],"rb") as f:print(hashlib.file_digest(f,"sha256").hexdigest())\n')
    sha_tool.chmod(0o755)
    for label, expected in [('unchanged', 0), ('before', 90), ('during', 91)]:
        fixture = work / ('shell-' + label)
        shutil.copytree(failing / 'stage', fixture)
        called = work / (label + '-query-called')
        module_path = fixture / 'loaders/libpixbufloader-bmp.so'
        if label == 'before':
            module_path.write_bytes(module_path.read_bytes() + b'changed')
        glue = ('timeout() { printf called > ' + shlex.quote(str(called)) + '; '
                + ('printf changed >> ' + shlex.quote(str(module_path)) + '; ' if label == 'during' else '')
                + "printf 'NATIVE_STUB\\n'; return 0; }\n")
        script = production.replace('/tmp/ember-pixbuf.AbCd1234', str(fixture))
        result = capture('shell-' + label, ['sh', '-s'], data=(glue + script).encode())
        require(result.returncode == expected and called.exists() == (label != 'before'),
                'production shell hash checks failed: ' + label)
        require(result.stdout == (b'NATIVE_STUB\n' if expected == 0 else b''),
                'production shell exposed unverified output: ' + label)

    # The upstream printer regression retains its failure status after output.
    host_printer = work / 'host-printer'
    template = work / 'thumbnailer.in'
    template.write_text('Exec=@bindir@/gdk-pixbuf-thumbnailer\nMimeType=@mimetypes@\n')
    generator = source / 'build-aux/gen-thumbnailer.py'
    command = [python, generator, '--printer', host_printer, '--pixdata', query,
               '--loaders', cache_input, '--bindir', '/usr/pkg/bin', template, work / 'thumbnailer.out']
    host_printer.write_text("#!/bin/sh\nprintf 'image/png;'\nexit 7\n"); host_printer.chmod(0o755)
    failure = capture('printer-failure', command)
    require(failure.returncode == 7 and not (work / 'thumbnailer.out').exists(), 'printer exit status was lost')
    host_printer.write_text("#!/bin/sh\nprintf 'image/png;'\n")
    success = capture('printer-success', command)
    require(success.returncode == 0 and (work / 'thumbnailer.out').read_text() ==
            'Exec=/usr/pkg/bin/gdk-pixbuf-thumbnailer\nMimeType=image/png;\n', 'ordinary printer output changed')
    # Keep --runner as two literal paths. The generator isolates its own
    # SDK helper child even when pkgsrc changes the generator's sys.platform.
    runner_python = work / 'host python with spaces'
    runner_python.symlink_to(python)
    runner_helper = work / "runner helper 'literal$;.py"
    runner_helper.write_text("""import json, os, sys
with open(os.environ['RUNNER_PROBE_RECEIPT'], 'w') as output:
    json.dump(dict(argv=sys.argv[1:], platform=sys.platform,
                   ignore_environment=sys.flags.ignore_environment,
                   no_site=sys.flags.no_site,
                   library_path=os.environ.get('LD_LIBRARY_PATH'),
                   loaders=os.environ.get('GDK_PIXBUF_MODULE_FILE')), output)
print('image/png;', end='')
sys.exit(int(os.environ['RUNNER_PROBE_STATUS']))
""")
    pysite = work / 'runner target pysite'
    pysite.mkdir()
    (pysite / 'sitecustomize.py').write_text('import sys\nsys.platform = "netbsd11"\n')
    literal_printer = work / "target printer 'literal$;"
    literal_cache = work / "target cache 'literal$;"
    runner_output = work / 'runner thumbnailer.out'
    for label, status in [('success', 0), ('failure', 7)]:
        runner_output.unlink(missing_ok=True)
        probe = work / ('runner-' + label + '.json')
        result = capture('runner-' + label, [python, generator, '--runner',
            runner_python, runner_helper, '--printer', literal_printer, '--pixdata', query,
            '--loaders', literal_cache, '--bindir', '/usr/pkg/bin', template, runner_output],
            changes={'PYTHONPATH': str(pysite), 'RUNNER_PROBE_RECEIPT': str(probe),
                     'RUNNER_PROBE_STATUS': str(status), 'LD_LIBRARY_PATH': 'literal target library path'})
        require(result.returncode == status and not result.stdout,
                'thumbnailer runner status changed: ' + label)
        observed = json.loads(probe.read_text())
        require(observed == dict(argv=['--mime', str(literal_printer), str(literal_cache)],
            platform=sys.platform, ignore_environment=1, no_site=1,
            library_path='literal target library path', loaders=str(literal_cache)),
            'thumbnailer runner flags, literal paths or target environment changed: ' + label)
        if status:
            require(not runner_output.exists(), 'failed runner published thumbnailer metadata')
        else:
            require(runner_output.read_text() ==
                'Exec=/usr/pkg/bin/gdk-pixbuf-thumbnailer\nMimeType=image/png;\n',
                'isolated runner thumbnailer metadata changed')
    inputs = {str(path):digest(path) for path in [helper, generator, readelf, cc, python]}
    (work / 'result.json').write_text(json.dumps(dict(result='PASS', inputs_sha256=inputs, commands=receipts,
        local_refusals=23, mocked_transport_cases=len(transport), upstream_printer_cases=2, upstream_runner_cases=2, production_shell_hash_cases=3,
        scope='Real GCC16 ELF headers/providers, SDK JSON/hash checks and mocked SSH. No target execution or installed package acceptance.'),indent=2)+'\n')
    print('PASS: 23 local refusals, 12 loader/MIME transport contracts, 3 production shell hash controls and 2 upstream printer plus 2 isolated runner controls')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
