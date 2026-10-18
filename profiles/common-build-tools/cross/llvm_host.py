# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Policy shared by the native LLVM/Clang generator commands."""
import os
from pathlib import Path
import sys
import tarfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'recipes/lang/llvm/files'))
from sdk_source import load_sdk

SOURCE = 'llvm-project-23.1.3.src'
SOURCE_SHA = 'c44186a7762ed28954be72e5ff6df9808e0779d4f1bf014ecc4e7e211d31ee34'


def checked_paths(values):
    from emberbsd_sdk.paths import canonical_new
    from emberbsd_sdk.errors import SDKError
    for path in values:
        if not os.path.isabs(path):
            raise SDKError('Absolute paths required')
        canonical_new(path)


def query(argv):
    from emberbsd_sdk.process import capture
    return capture(argv).stdout.decode().strip()


def log_run(path, argv, cwd=None):
    from emberbsd_sdk.process import run_logged
    run_logged(argv, str(path), cwd=cwd)


def extract_source(archive, destination, components=None):
    # The caller authenticates the upstream release before this operation.
    with tarfile.open(archive, 'r:*') as source:
        members = [m for m in source.getmembers() if components is None or any(m.name == SOURCE + '/' + p or m.name.startswith(SOURCE + '/' + p + '/') for p in components)]
        if not members:
            raise ValueError('Empty selected upstream source')
        source.extractall(destination, members=members, filter='data')


def native(kind, arguments):
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.errors import SDKError
    expected = 4 if kind == 'llvm' else 5
    if len(arguments) != expected:
        raise SDKError('Use LLVM_ARCHIVE [LLVM_NATIVE] NEW_WORK CMAKE NINJA')
    if kind == 'llvm':
        archive, work, cmake, ninja = arguments
        llvm = None
    else:
        archive, llvm, work, cmake, ninja = arguments
    checked_paths(arguments)
    jobs = os.environ.get('JOBS', '3')
    if not jobs.isdigit() or int(jobs) < 1:
        raise SDKError('JOBS must be positive')
    host_python = os.environ.get('HOST_PYTHON', sys.executable)
    checked_paths([host_python])
    tools = [cmake, ninja, host_python, os.environ.get('HOST_CC', '/usr/bin/cc'), os.environ.get('HOST_CXX', '/usr/bin/c++')]
    if not all(os.access(p, os.X_OK) for p in tools):
        raise SDKError('Executable native tools required')
    if sha256_file(archive) != SOURCE_SHA:
        raise SDKError('Pinned LLVM source archive SHA256 differs')
    if llvm and (not Path(llvm, 'lib/cmake/llvm/LLVMConfig.cmake').is_file() or query([llvm + '/bin/llvm-config', '--version']) != '23.1.3'):
        raise SDKError('Matching native LLVM build required')
    os.mkdir(work)
    os.mkdir(work + '/source')
    extract_source(archive, work + '/source', ['llvm', 'cmake', 'third-party', 'libc'] if kind == 'llvm' else ['clang', 'cmake'])
    import emberbsd_sdk
    api = Path(emberbsd_sdk.__file__).resolve().parent
    entrypoint = Path(__file__).with_name('build-' + kind + '-native.py')
    loader = Path(__file__).resolve().parents[1] / 'recipes/lang/llvm/files/sdk_source.py'
    inputs = [archive, __file__, str(entrypoint), str(loader), *tools,
              *[str(p) for p in sorted(api.rglob('*.py'))]]
    if llvm:
        inputs.extend([llvm + '/bin/llvm-config', llvm + '/bin/llvm-tblgen'])
    hashes = {p: sha256_file(os.path.realpath(p)) for p in inputs}
    write_json(work + '/inputs.json', dict(sha256=hashes, versions={p: query([p, '--version']) for p in tools}, jobs=int(jobs)))
    command = [cmake, '-S', work + '/source/' + SOURCE + '/' + kind, '-B', work + '/native', '-G', 'Ninja',
        '-DCMAKE_C_COMPILER=' + tools[3], '-DCMAKE_CXX_COMPILER=' + tools[4], '-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_MAKE_PROGRAM=' + ninja, '-DPython3_EXECUTABLE=' + host_python]
    if kind == 'llvm':
        command += ['-DLLVM_TARGETS_TO_BUILD=Native'] + ['-DLLVM_' + option + '=OFF' for option in ('INCLUDE_TESTS', 'INCLUDE_BENCHMARKS', 'INCLUDE_EXAMPLES', 'ENABLE_ZLIB', 'ENABLE_ZSTD', 'ENABLE_LIBXML2', 'ENABLE_TERMINFO', 'ENABLE_LIBEDIT')]
        outputs = ['llvm-tblgen', 'llvm-min-tblgen', 'llvm-config']
    else:
        command += ['-DLLVM_DIR=' + llvm + '/lib/cmake/llvm', '-DLLVM_CMAKE_DIR=' + llvm + '/lib/cmake/llvm', '-DLLVM_CONFIG=' + llvm + '/bin/llvm-config', '-DLLVM_TABLEGEN=' + llvm + '/bin/llvm-tblgen', '-DLLVM_INCLUDE_TESTS=OFF', '-DCLANG_INCLUDE_TESTS=OFF']
        outputs = ['clang-tblgen']
    log_run(work + '/configure.log', command)
    log_run(work + '/build.log', [ninja, '-C', work + '/native', '-j', jobs, *outputs])
    result = {}
    for tool in outputs:
        path = work + '/native/bin/' + tool
        version = query([path, '--version'])
        if '23.1.3' not in version:
            raise SDKError('Unexpected native generator version: ' + tool)
        result[tool] = dict(sha256=sha256_file(path), version=version)
    if hashes != {p: sha256_file(os.path.realpath(p)) for p in inputs}:
        raise SDKError('Native build input changed')
    write_json(work + '/outputs.json', result)
    print('Build-host generators: ' + work + '/native/bin')
