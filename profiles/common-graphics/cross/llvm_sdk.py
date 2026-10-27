# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). LLVM policy over the explicit SDK host API1.
"""Load shared host mechanisms. Keep LLVM semantics in this profile."""
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile

sys.dont_write_bytecode = True
_adapter = Path(__file__).resolve().parents[2] / 'development-toolchain/runtime/recipe/files'
sys.path.insert(0, str(_adapter))
import sdk_source


def initialize(argv):
    if sys.version_info[:2] != (3, 15):
        raise RuntimeError('Host Python 3.15 is required')
    args = sdk_source.arguments(argv)
    sdk_source.install_signal_handlers()
    from emberbsd_sdk import API_VERSION
    from emberbsd_sdk.stream import PRODUCER_STREAM_API
    if type(API_VERSION) is not int or API_VERSION != 1 or type(PRODUCER_STREAM_API) is not int or PRODUCER_STREAM_API != 1:
        raise RuntimeError('SDK host API1 with producer stream API1 is required')
    return args


def digest(path):
    from emberbsd_sdk.inventory import sha256_file
    return sha256_file(str(Path(path).resolve(strict=True)))


def environment(overrides=None):
    from emberbsd_sdk.process import sanitized_environment
    env = sanitized_environment()
    if overrides:
        env.update({k: str(v) for k, v in overrides.items() if v is not None})
        for key, value in overrides.items():
            if value is None:
                env.pop(key, None)
    return env


def capture(*argv, env=None):
    from emberbsd_sdk.errors import CommandError
    out, err, status = query(*argv, env=env)
    if status:
        raise CommandError(status, list(map(str, argv)), out.encode(), err.encode())
    return out.strip()


def query(*argv, env=None):
    from emberbsd_sdk.errors import CommandError, SDKError
    from emberbsd_sdk.stream import capture_streamed
    try:
        result = capture_streamed(list(map(str, argv)), env=environment(env),
                                  stdout_limit=16 * 1024 * 1024, stderr_limit=1024 * 1024, timeout=120)
        if result.stderr_truncated:
            raise SDKError('producer stderr exceeds the capture limit')
        return result.value.decode('utf-8'), result.stderr.decode('utf-8'), 0
    except CommandError as error:
        if getattr(error, 'stdout_truncated', False) or getattr(error, 'stderr_truncated', False):
            raise SDKError('failed producer output exceeds the capture limit') from error
        return error.stdout.decode('utf-8'), error.stderr.decode('utf-8'), error.returncode


def produce(argv, log):
    from emberbsd_sdk.errors import ProcessOwnershipError
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.process import run_logged
    try:
        run_logged(list(map(str, argv)), str(log), env=environment({
            'TMPDIR': str(Path(log).parent),
            'NATIVE_CXX': os.environ.get('NATIVE_CXX'),
        }))
    except ProcessOwnershipError as e:
        marker = Path(log).parent / sdk_source.PRODUCER_QUARANTINE
        if not marker.exists():
            write_json(str(marker), {'error': str(e), 'log': str(log)})
        raise


def safe_absolute(path):
    return isinstance(path, str) and path.startswith('/') and not re.search(r'[\s\x00-\x1f\x7f]', path) and '..' not in path.split('/')


def existing_directory(path):
    if not safe_absolute(path) or not Path(path).is_dir():
        raise ValueError('expected existing absolute directory: ' + str(path))
    real = str(Path(path).resolve(strict=True))
    if not safe_absolute(real):
        raise ValueError('unsafe resolved input path: ' + path)
    return real


def new_destination(path, inputs=()):
    from emberbsd_sdk import paths
    if not safe_absolute(path):
        raise ValueError('NEW_WORK must be absolute without whitespace/control characters')
    path = paths.canonical_new(path)
    if paths.entry(path) is not None:
        raise ValueError('NEW_WORK must be absolute and absent')
    for root in inputs:
        paths.reject_overlap(path, root)
    paths.real_directory(str(Path(path).parent))
    return path


def stage_for(destination):
    from emberbsd_sdk.publication import require_directory_publication
    require_directory_publication()
    return tempfile.mkdtemp(prefix='.' + Path(destination).name + '.partial-', dir=Path(destination).parent)


def publish(stage, destination):
    from emberbsd_sdk.publication import publish_directory_noreplace
    publish_directory_noreplace(stage, destination)


def command_file(path, argv):
    Path(path).write_text(shlex.join(list(map(str, argv))) + '\n')


def read_json(path):
    from emberbsd_sdk.jsonio import read_json as read
    return read(str(path))


def write_json(path, value):
    from emberbsd_sdk.jsonio import write_json as write
    write(str(path), value)


def main(function):
    try:
        return function(initialize(sys.argv[1:]))
    except Exception as error:
        print(f'{Path(sys.argv[0]).stem}: {error}', file=sys.stderr)
        return 1
