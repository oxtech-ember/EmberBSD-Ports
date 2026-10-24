# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Policy shared by the native LLVM/Clang generator commands."""
import os
from pathlib import Path
import shlex
import sys
import tarfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '../../pkgsrc/lang/llvm/files'))
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


def log_run(path, argv, cwd=None, env=None):
    from emberbsd_sdk.process import run_logged
    run_logged(argv, str(path), cwd=cwd, env=env)


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
    from emberbsd_sdk.native_toolset import NATIVE_TOOLSET_API, load_native_toolset
    if type(NATIVE_TOOLSET_API) is not int or NATIVE_TOOLSET_API != 1:
        raise SDKError('SDK native toolset API 1 is required')
    bindings = ('DESCRIPTOR', 'DESCRIPTOR_SHA256', 'PRODUCER_RECEIPT',
                'PRODUCER_RECEIPT_SHA256')
    selected = {name: os.environ.get('EMBERBSD_NATIVE_TOOLSET_' + name)
                for name in bindings}
    if not all(selected.values()):
        raise SDKError('Set all four EMBERBSD_NATIVE_TOOLSET inputs')
    roles = ('cc', 'cxx', 'cpp', 'as', 'ld', 'ar', 'ranlib', 'nm', 'strip',
             'cmake', 'ninja', 'python', 'pkg-config', 'sh')
    if kind == 'clang':
        roles += ('llvm-config', 'llvm-tblgen')
    toolset = load_native_toolset(
        selected['DESCRIPTOR'], descriptor_sha256=selected['DESCRIPTOR_SHA256'],
        accepted_producer_receipt={'path': selected['PRODUCER_RECEIPT'],
                                   'sha256': selected['PRODUCER_RECEIPT_SHA256']},
        required_roles=roles)
    if Path(sys.executable).resolve(strict=True) != Path(toolset.tool('python')).resolve(strict=True):
        raise SDKError('The controller interpreter differs from the selected SDK Python')
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
    host_python = toolset.tool('python')
    for variable, role in (('HOST_CC', 'cc'), ('HOST_CXX', 'cxx'),
                           ('HOST_PYTHON', 'python')):
        if variable in os.environ and os.environ[variable] != toolset.tool(role):
            raise SDKError(variable + ' differs from the selected SDK tool')
    if cmake != toolset.tool('cmake') or ninja != toolset.tool('ninja'):
        raise SDKError('CMake and Ninja must match the selected SDK toolset')
    if llvm and any(llvm + '/bin/' + role != toolset.tool(role)
                    for role in ('llvm-config', 'llvm-tblgen')):
        raise SDKError('Native LLVM generators must match the selected SDK toolset')
    tools = [cmake, ninja, host_python, toolset.tool('cc'), toolset.tool('cxx')]
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
    loader = Path(__file__).resolve().parents[1] / '../../pkgsrc/lang/llvm/files/sdk_source.py'
    inputs = [archive, __file__, str(entrypoint), str(loader), *tools,
              *[str(p) for p in sorted(api.rglob('*.py'))]]
    if llvm:
        inputs.extend([llvm + '/bin/llvm-config', llvm + '/bin/llvm-tblgen'])
    hashes = {p: sha256_file(os.path.realpath(p)) for p in inputs}
    write_json(work + '/inputs.json', dict(sha256=hashes, versions={p: query([p, '--version']) for p in tools}, jobs=int(jobs), native_toolset=toolset.as_dict()))
    command = [cmake, '-S', work + '/source/' + SOURCE + '/' + kind, '-B', work + '/native', '-G', 'Ninja',
        '-DCMAKE_C_COMPILER=' + tools[3], '-DCMAKE_CXX_COMPILER=' + tools[4], '-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_MAKE_PROGRAM=' + ninja, '-DPython3_EXECUTABLE=' + host_python]
    command += ['-DCMAKE_' + name + '=' + toolset.tool(role) for name, role in
                (('ASM_COMPILER', 'as'), ('LINKER', 'ld'), ('AR', 'ar'),
                 ('RANLIB', 'ranlib'), ('NM', 'nm'), ('STRIP', 'strip'))]
    flags = toolset.abi_flags
    command += ['-DCMAKE_C_FLAGS=' + shlex.join(flags['cppflags'] + flags['cflags']),
                '-DCMAKE_CXX_FLAGS=' + shlex.join(flags['cppflags'] + flags['cxxflags'])]
    command += ['-DCMAKE_' + kind + '_LINKER_FLAGS=' + shlex.join(flags['ldflags'])
                for kind in ('EXE', 'SHARED', 'MODULE')]
    command += ['-DPKG_CONFIG_EXECUTABLE=' + toolset.tool('pkg-config')]
    if kind == 'llvm':
        command += ['-DLLVM_TARGETS_TO_BUILD=Native'] + ['-DLLVM_' + option + '=OFF' for option in ('INCLUDE_TESTS', 'INCLUDE_BENCHMARKS', 'INCLUDE_EXAMPLES', 'ENABLE_ZLIB', 'ENABLE_ZSTD', 'ENABLE_LIBXML2', 'ENABLE_TERMINFO', 'ENABLE_LIBEDIT')]
        outputs = ['llvm-tblgen', 'llvm-min-tblgen', 'llvm-config']
    else:
        command += ['-DLLVM_DIR=' + llvm + '/lib/cmake/llvm', '-DLLVM_CMAKE_DIR=' + llvm + '/lib/cmake/llvm', '-DLLVM_CONFIG=' + llvm + '/bin/llvm-config', '-DLLVM_TABLEGEN=' + llvm + '/bin/llvm-tblgen', '-DLLVM_INCLUDE_TESTS=OFF', '-DCLANG_INCLUDE_TESTS=OFF']
        outputs = ['clang-tblgen']
    from emberbsd_sdk.process import sanitized_environment
    env = sanitized_environment()
    for key in ('CC', 'CXX', 'CPP', 'AS', 'LD', 'AR', 'RANLIB', 'NM', 'STRIP',
                'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CPATH',
                'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH', 'SDKROOT',
                'PKG_CONFIG_PATH', 'PKG_CONFIG_LIBDIR', 'PKG_CONFIG_SYSROOT_DIR'):
        env.pop(key, None)
    env['PATH'] = os.pathsep.join(dict.fromkeys(str(Path(toolset.tool(role)).parent)
                                               for role in roles))
    env['SHELL'] = toolset.tool('sh')
    env['PKG_CONFIG'] = toolset.tool('pkg-config')
    log_run(work + '/configure.log', command, env=env)
    log_run(work + '/build.log', [ninja, '-C', work + '/native', '-j', jobs, *outputs], env=env)
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
