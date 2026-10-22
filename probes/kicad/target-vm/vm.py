# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Private query guest policy and shared SDK binding.
"""Host policy for the private AArch64 query guest; no import-time side effects."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

OWNER = Path(__file__).resolve().parent
DEFAULT_RAM_MIB = 1024
FSTAT_METADATA = './usr/bin/fstat type=file uid=0 gname=kmem mode=02555\n'


def ram_mib(value=DEFAULT_RAM_MIB):
    if type(value) is int:
        result = value
    elif isinstance(value, str) and re.fullmatch('[0-9]+', value):
        result = int(value)
    else:
        raise ValueError('RAM must be an integer from 1024 to 8192 MiB')
    if not 1024 <= result <= 8192:
        raise ValueError('RAM must be an integer from 1024 to 8192 MiB')
    return result


def integer(value, low, high, label):
    if type(value) is not int and not (isinstance(value, str) and re.fullmatch('[0-9]+', value)):
        raise ValueError(f'{label} must be an integer from {low} to {high}')
    result = int(value)
    if not low <= result <= high:
        raise ValueError(f'{label} must be an integer from {low} to {high}')
    return result


def parser(description, names):
    result = argparse.ArgumentParser(description=description)
    result.add_argument('--sdk-source', required=True, type=Path)
    for name in names:
        result.add_argument(name, type=Path)
    return result


def sdk(source):
    if sys.version_info[:2] != (3, 15):
        raise SystemExit('Use the qualified native Python 3.15 interpreter.')
    source = source.resolve(strict=True)
    sys.path.insert(0, str(source / 'src'))
    import emberbsd_sdk
    if emberbsd_sdk.API_VERSION != 1 or Path(emberbsd_sdk.__file__).resolve().parent != source / 'src/emberbsd_sdk':
        raise SystemExit('The selected SDK source must provide host API 1.')
    from emberbsd_sdk import inventory, jsonio, paths, process, process_identity
    from emberbsd_sdk.errors import SDKError
    if process_identity.PROCESS_IDENTITY_API != 1:
        raise SDKError('SDK process identity API 1 is required.')
    return inventory, jsonio, paths, process, process_identity


def sdk_record(source, inventory):
    from emberbsd_sdk.provenance import git_source
    result = git_source(str(source.resolve()), env=dict(os.environ))
    result.update(api=1, process_identity_api=1, files_sha256={
        name: inventory.sha256_file(source.resolve() / 'src/emberbsd_sdk' / name)
        for name in ['process_identity.py', '_darwin_process.py', 'process.py', 'jsonio.py', 'inventory.py']})
    return result


def canonical(path):
    result = path.resolve(strict=True)
    if not path.is_absolute() or path != result or not re.fullmatch(r'/[A-Za-z0-9_./+-]+', str(path)):
        raise ValueError('Use simple absolute canonical paths.')
    return result


def write(path, data, mode=0o600):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data.encode('utf-8') if isinstance(data, str) else data)


def root_metadata(source_etc, tools, run):
    source = source_etc / 'mtree/NetBSD.dist.base'
    roots = [line for line in source.read_text().splitlines() if not line.lstrip().startswith('#') and line.split()[:1] == ['.']]
    if len(roots) != 1:
        raise ValueError('Expected one root declaration in the pinned fork mtree source')
    flat = run('root-metadata', tools / 'nbmtree', '-C', '-N', source_etc, '-f', source).decode()
    records = [line for line in flat.splitlines() if line.split()[:1] == ['.']]
    expected = sorted(['type=dir', 'uid=0', 'gid=0', 'mode=0755'])
    if len(records) != 1 or sorted(records[0].split()[1:]) != expected:
        raise ValueError('Pinned fork root must resolve to root:wheel (0:0), directory mode 0755')
    return records[0] + '\n'


def owned_identity(work, record, identity):
    pid = integer((work / 'runner.pid').read_text().strip(), 2, 2147483647, 'runner PID')
    expected = record['argv']
    if not isinstance(expected, list) or not expected or any(not isinstance(arg, str) for arg in expected):
        raise ValueError('Invalid recorded QEMU arguments.')
    current = identity.process_identity(pid)
    if current is None:
        return pid, None
    if (list(current.argv) != expected or current.executable != expected[0] or
            str(current.birth) != record['process_start_time'] or
            current.backend != record['process_identity_backend'] or
            f'file={work}/query.ffs,if=none,format=raw,id=root' not in current.argv):
        raise ValueError('recorded PID is not the owned QEMU guest')
    return pid, current


def command_log(work, name, expected, command, *, env=None, timeout=120, log_directory=None):
    result = subprocess.run([str(arg) for arg in command], env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    write((log_directory or work / 'logs') / f'check-{name}.log', f'exit={result.returncode}\n'.encode() + result.stdout + result.stderr)
    if result.returncode != expected:
        raise ValueError(f'{name}: expected {expected}, got {result.returncode}')
    return result.stdout


def entrypoint(main):
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
