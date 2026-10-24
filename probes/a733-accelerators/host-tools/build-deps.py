#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted). Port of the native dependency shell.
"""Build the pinned native SPIR-V dependencies without nested controllers."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'pkgsrc/lang/llvm/files'))
import sdk_source

SOURCE_PINS = {
    'SPIRV-Headers': '496543121ce6419f23d6fa5d7194ba66c36212d2',
    'SPIRV-LLVM-Translator': 'e65dde28ce8f12ef7245914fa2850260328669e4',
}


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def native_options(root, sdk, macsdk):
    return ['-DCMAKE_C_COMPILER=' + str(sdk / 'bin/clang'),
            '-DCMAKE_CXX_COMPILER=' + str(sdk / 'bin/clang++'),
            '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CXX_FLAGS_RELEASE=-O2',
            '-DCMAKE_OSX_SYSROOT=' + macsdk, '-DCMAKE_LINKER_TYPE=LLD',
            '-DCMAKE_EXE_LINKER_FLAGS=-Wl,--lto-O1,--lto-CGO1 -nostdlib++ ' + macsdk + '/usr/lib/libc++.tbd -Wl,-cache_path_lto,' + str(root / 'cache/lto'),
            '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']


def build(arguments):
    from emberbsd_sdk.process import capture, run_logged, sanitized_environment
    if len(arguments) != 3:
        raise ValueError('Use build-deps.py --sdk-source SDK WORK LLVM_SDK HOST_PREFIX')
    if any(not str(value).startswith('/') for value in arguments):
        raise ValueError('Absolute paths are required')
    root, sdk, host = [Path(value).resolve(strict=True) for value in arguments]
    python = Path(os.environ.get('HOST_PYTHON', str(host / 'bin/python3.15')))
    cmake = Path(os.environ.get('CMAKE', str(host / 'bin/cmake')))
    if not all(os.access(path, os.X_OK) for path in (python, cmake)):
        raise ValueError('Executable native Python and CMake are required')
    environment = sanitized_environment()
    environment.update(PATH=f'{sdk}/bin:{host}/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
                       PKG_CONFIG_PATH=str(root / 'prefix/lib/pkgconfig'))
    def query(argv):
        return capture(list(map(str, argv)), env=environment).stdout.decode('utf-8').strip()
    if query([sdk / 'bin/llvm-config', '--version']) != '23.1.4':
        raise ValueError('Matching native LLVM 23.1.4 is required')
    for name, revision in SOURCE_PINS.items():
        source = root / 'src' / name
        if query(['git', '-C', source, 'rev-parse', 'HEAD']) != revision or query(['git', '-C', source, 'status', '--porcelain']):
            raise ValueError('Wrong or modified Khronos source: ' + name)
    for name in ('tmp', 'cache/lto', 'logs'):
        (root / name).mkdir(parents=True, exist_ok=True)
    environment.update(TMPDIR=str(root / 'tmp'), TMP=str(root / 'tmp'), TEMP=str(root / 'tmp'))
    macsdk = query(['/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-path'])
    jobs = os.environ.get('JOBS', '4')
    if not jobs.isdigit() or int(jobs) < 1:
        raise ValueError('JOBS must be positive')

    def helper(module, function, argv):
        # Keep the helper in this controller. Its SDK command capture is not
        # wrapped by another owned process that can preempt its drain.
        previous = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(environment)
            getattr(load(module), function)(argv)
        finally:
            os.environ.clear()
            os.environ.update(previous)

    helper('apply-spirv-tools-patches', 'apply', [str(root / 'src/SPIRV-Tools')])
    def run(argv, name):
        run_logged(list(map(str, argv)), str(root / 'logs' / (name + '.log')), env=environment)
    def configure(name, source, extra):
        run([cmake, '-S', source, '-B', root / 'build' / name, '-G', 'Ninja',
             '-DCMAKE_INSTALL_PREFIX=' + str(root / 'prefix'), *extra], name + '-configure')
    def install(name):
        run([cmake, '--install', root / 'build' / name], name + '-install')
    def compile(name):
        run([cmake, '--build', root / 'build' / name, '--parallel', jobs], name + '-build')

    configure('headers', root / 'src/SPIRV-Headers', ['-DSPIRV_HEADERS_ENABLE_TESTS=OFF'])
    install('headers')
    configure('spirv-tools', root / 'src/SPIRV-Tools', [*native_options(root, sdk, macsdk),
        '-DSPIRV-Headers_SOURCE_DIR=' + str(root / 'src/SPIRV-Headers'),
        '-DPython3_EXECUTABLE=' + str(python), '-DSPIRV_SKIP_TESTS=ON',
        '-DSPIRV_SKIP_EXECUTABLES=OFF', '-DBUILD_SHARED_LIBS=OFF', '-DSPIRV_WERROR=ON'])
    compile('spirv-tools')
    order = Path(tempfile.mkdtemp(prefix='link-order-', dir=root / 'build'))
    helper('check-spirv-link-order', 'check', [str(root / 'build/spirv-tools/tools'), str(order / 'result')])
    install('spirv-tools')
    configure('translator', root / 'src/SPIRV-LLVM-Translator', [*native_options(root, sdk, macsdk),
        '-DLLVM_DIR=' + str(sdk / 'lib/cmake/llvm'),
        '-DLLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR=' + str(root / 'src/SPIRV-Headers'),
        '-DLLVM_SPIRV_INCLUDE_TESTS=OFF', '-DLLVM_ENABLE_ASSERTIONS=ON',
        '-DLLVM_SPIRV_ENABLE_LIBSPIRV_DIS=ON', '-DBUILD_SHARED_LIBS=OFF'])
    compile('translator')
    install('translator')


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    try:
        if sys.version_info[:2] != (3, 15):
            raise ValueError('Host Python 3.15 is required')
        _, arguments = sdk_source.load_sdk()
        build(arguments)
    except Exception as error:
        sdk_source.exit_error(error)
