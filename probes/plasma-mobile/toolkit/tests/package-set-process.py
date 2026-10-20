#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual auditor CLI and owned-process controls.
"""Use native package fixtures. Never install packages or execute payloads."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import io
import json
import os
import shlex
import shutil
import signal
import subprocess
import tarfile
import time
from types import SimpleNamespace
from unittest.mock import patch
from package_set_fixture import Fixture, check


def main():
    f = Fixture(sys.argv[1:])
    payload = f.work / 'payload'
    payload.mkdir()
    (payload / 'leaf').write_bytes(b'Leaf bytes\n')
    (payload / 'root').write_bytes(b'Root bytes\n')
    database = f.work / 'pkgdb'
    archives = []
    for name in ('leaf', 'root'):
        archive = f.package(f.work / 'cache', 'process-' + name + '-1.0',
                            payload, [name], dependencies='process-leaf>=1.0' if name == 'root' else None)
        archives.append(archive)
        f.database(archive, database)
    index = f.work / 'archives.txt'
    index.write_text(''.join(str(path) + '\n' for path in archives))
    roots = ['process-root-1.0']
    python = [sys.executable, '-B', '-I', '-S']
    def command(destination, sdk=None):
        return python + [str(f.auditor), '--sdk-source', str(sdk or f.sdk),
                         str(database), str(index), str(destination), *roots]
    def shell(name, body):
        path = f.work / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)
        return str(path)
    def reject(name, env, code, message, argv=None):
        destination = f.work / name
        result = f.status(argv or command(destination), env=env)
        f.result(name, result, message, destination)
        check(result.returncode == code, f'{name}: wrong status {result.returncode}')
        return result
    valid = f.work / 'valid-cli'
    f.result('valid-cli', f.status(command(valid)), destination=valid)
    restricted = f.work / 'restrictive-umask'
    result = f.status(['sh', '-c', 'umask 077; exec "$@"', 'sh', *command(restricted)])
    f.result('restrictive-umask', result, destination=restricted)
    for archive in archives:
        check((restricted / 'packages' / archive.name).stat().st_mode & 0o7777 ==
              archive.stat().st_mode & 0o7777, 'Archive copy lost source mode')
    fatal = shell('fatal', 'printf reason >&2; exit 97')
    reject('version-97', dict(f.env, BSDTAR=fatal), 97, 'reason')
    reject('dependency-97', dict(f.env, PKG_INFO=fatal), 97, 'reason')
    for option in ('-xOf', '-cf'):
        wrapper = shell('tar-' + option[1:],
                        f'if [ "$1" = {shlex.quote(option)} ]; then printf reason >&2; exit 97; fi\n'
                        f'exec {shlex.quote(f.tar)} "$@"')
        reject('archive-' + option[1:] + '-97', dict(f.env, BSDTAR=wrapper), 97, 'reason')
    terminated = shell('terminated', 'kill -TERM $$')
    reject('producer-signal', dict(f.env, BSDTAR=terminated), 143, 'command failed (-15)')
    marker = f.work / 'unexpected-producer'
    forbidden = shell('forbidden', f'touch {shlex.quote(str(marker))}; exit 97')
    destination = f.work / 'wrong-target'
    argv = python + [str(f.auditor), '--sdk-source', f.sdk, '--target', 'unknown',
                     str(database), str(index), str(destination), *roots]
    reject('wrong-target', dict(f.env, BSDTAR=forbidden), 1, 'Unsupported target', argv)
    check(not marker.exists(), 'Invalid target started a producer')
    for module, constant in (('stream', 'PRODUCER_STREAM_API'), ('tarstream', 'TAR_STREAM_API')):
        sdk = f.work / ('old-sdk-' + module)
        shutil.copytree(Path(f.sdk) / 'src', sdk / 'src')
        path = sdk / 'src/emberbsd_sdk' / (module + '.py')
        path.write_text(path.read_text().replace(constant + ' = 1', constant + ' = 0'))
        destination = f.work / ('old-' + module)
        reject('old-' + module, dict(f.env, BSDTAR=forbidden), 1,
               'lacks producer-stream/raw-tar', command(destination, sdk))
        check(not marker.exists(), 'Old SDK started a producer')

    # The actual CLI owns INT/TERM/HUP. Its producer starts another process
    # group in the same session. Both must stop before staging is removed.
    producer = f.work / 'writer.py'
    producer.write_text('''import os,signal,sys,time
from pathlib import Path
root=Path(sys.argv[1])
if os.fork()==0:
    os.setpgid(0,0)
    signal.signal(signal.SIGTERM,signal.SIG_IGN)
    (root/'writer.pid').write_text(str(os.getpid()))
    until=time.monotonic()+20
    while time.monotonic()<until:
        with (root/'writes').open('ab') as handle: handle.write(b'x')
        time.sleep(.02)
    os._exit(0)
while not (root/'writer.pid').exists(): time.sleep(.01)
(root/'ready').write_text(str(os.getpid()))
time.sleep(20)
''')
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        area = f.work / ('signal-' + str(number))
        area.mkdir()
        wrapper = shell('writer-' + str(number), 'exec ' + shlex.join(python + [str(producer), str(area)]))
        destination = area / 'set'
        child = subprocess.Popen(command(destination), env=dict(f.env, BSDTAR=wrapper),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        writer = None
        try:
            deadline = time.monotonic() + 15
            while not (area / 'ready').exists():
                check(child.poll() is None and time.monotonic() < deadline, 'Producer did not reach signal control')
                time.sleep(.02)
            writer = int((area / 'writer.pid').read_text())
            child.send_signal(number)
            out, err = child.communicate(timeout=15)
            (area / 'cli.log').write_bytes(out + err)
            check(child.returncode == 128 + number, 'CLI lost signal status')
            check(not destination.exists() and not list(area.glob('.set-*')), 'Signal published or left proven-drained staging')
            try:
                os.kill(writer, 0)
            except ProcessLookupError:
                pass
            else:
                raise AssertionError('Owned writer survived CLI return')
            before = (area / 'writes').read_bytes()
            time.sleep(.08)
            check((area / 'writes').read_bytes() == before, 'Writer changed work after return')
            f.count += 1
            print('PASS: signal-' + str(number))
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
                child.communicate(timeout=15)
            if writer is not None:
                try:
                    os.kill(writer, 0)
                except ProcessLookupError:
                    pass
                else:
                    raise AssertionError('Retain this fixture: writer still exists')

    # Inject uncertainty only after the real SDK stop has completed. A failed
    # marker write must not convert that uncertainty into cleanup permission.
    driver = f.work / 'uncertain.py'
    driver.write_text('''import importlib.util,sys
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('auditor',sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
load=m.load_sdk
def wrapped(argv):
    result=load(argv)
    from emberbsd_sdk import stream
    stop=stream.OwnedProcessGroup.stop
    def uncertain(group):
        stop(group)
        raise m.ProcessOwnershipError(group.pid,'injected after real drain')
    stream.OwnedProcessGroup.stop=uncertain
    if sys.argv[2]=='marker-fails':
        def fail(*args): raise OSError('marker write failed')
        m.write_json=fail
    return result
m.load_sdk=wrapped
raise SystemExit(m.main(sys.argv[3:]))
''')
    for mode in ('marker-written', 'marker-fails'):
        destination = f.work / mode
        argv = python + [str(driver), str(f.auditor), mode] + command(destination)[5:]
        result = f.status(argv)
        check(result.returncode == 1 and not destination.exists(), 'Unproven ownership published output')
        retained = list(f.work.glob('.' + mode + '-*'))
        check(len(retained) == 1, 'Unproven ownership lost staging')
        check(b'cannot prove the drain of owned session' in result.stderr and
              str(retained[0]).encode() in result.stderr, 'Ownership error or retained path was lost')
        receipt = retained[0] / '.producer-ownership-unproven.json'
        if mode == 'marker-written':
            data = json.loads(receipt.read_bytes())
            check(data['status'] == 'unproven' and data['sid'] > 0, 'Wrong quarantine identity')
        else:
            check(not receipt.exists() and b'marker write failed' in result.stderr, 'Marker failure not exercised')
        (f.work / (mode + '.log')).write_bytes(result.stdout + result.stderr)
        f.count += 1
        print('PASS: ' + mode)

    changed = database / 'process-leaf-1.0/+DESC'
    original = changed.read_bytes()
    audit_archive = f.module.audit_archive
    altered = False
    def change_metadata(tar, path, *args):
        nonlocal altered
        audit_archive(tar, path, *args)
        if not altered and '/packages/' in str(path):
            changed.chmod(0o644)
            changed.write_bytes(b'Changed after archive audit\n')
            altered = True
    destination = f.work / 'metadata-race'
    try:
        with patch.object(f.module, 'audit_archive', change_metadata):
            result = f.audit(database, index, destination, roots)
        check(altered, 'Metadata race did not occur')
        f.result('metadata-race', result, 'Installed metadata changed during audit', destination)
    finally:
        changed.write_bytes(original)

    # Use real SDK header and PAX traversal, without libarchive normalization.
    # This directly tests the package policy applied to raw producer bytes.
    f.module.load_sdk(['--sdk-source', f.sdk])
    def record(name, data=b'', kind=b'0'):
        header = tarfile.TarInfo(name)
        header.type, header.size = kind, len(data)
        return header.tobuf(format=tarfile.USTAR_FORMAT) + data + bytes((-len(data)) % 512)
    def pax(key, value):
        body = key + b'=' + value + b'\n'
        size = len(body) + 2
        while True:
            result = str(size).encode() + b' ' + body
            if len(result) == size:
                return result
            size = len(result)
    def parse(data):
        def raw(_argv, consume, **options):
            check(options['timeout'] == 300, 'Missing finite producer deadline')
            return SimpleNamespace(value=consume(io.BytesIO(data)))
        with patch.object(f.module, 'run_streamed', raw):
            return f.module.archive_members('unused', Path('unused'), {'elf': 183})
    accepted = record('global', pax(b'path', b'wrong'), b'g')
    accepted += record('local', pax(b'path', b''), b'x') + record('data', b'abc')
    check(parse(accepted)[b'data'][:2] == ('file', '900150983cd24fb0d6963f7d28e17f72'), 'Empty PAX override changed policy')
    f.count += 1
    for name, data, expected in [
        ('sparse', record('pax', pax(b'GNU.sparse.size', b'0'), b'x') + record('data'), 'Sparse'),
        ('pax-size', record('pax', pax(b'size', b'4'), b'x') + record('data', b'abc'), 'size override'),
        ('pax-orphan', record('pax', pax(b'path', b'data'), b'x'), 'no following member'),
        ('special', record('fifo', kind=b'6'), 'Unsupported archive member'),
        ('duplicate', record('data') * 2, 'Duplicate archive'),
        ('traversal', record('../data'), 'Invalid archive path'),
        ('truncated', record('data', b'abc')[:513], 'truncated tar record')]:
        try:
            parse(data)
        except f.module.AuditError as error:
            check(expected in str(error), f'{name}: wrong refusal {error}')
        else:
            raise AssertionError(name + ': policy accepted invalid bytes')
        f.count += 1
        print('PASS: ' + name)
    print(f'PASS: {f.count} CLI, producer-status, signal, ownership and raw-policy controls')


if __name__ == '__main__':
    main()
