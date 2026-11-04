#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that installed target llvm-config tables do not retain build paths."""
import json
import os
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    script = Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files/install-config-metadata.py'
    validator = Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files/llvm_config_validation.py'
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / 'src/llvm'
        build = source / 'build'
        sysroot = root / 'sysroot'
        tools = build / 'tools/llvm-config'
        destination = root / 'stage/usr/pkg/lib/cmake/llvm/emberbsd'
        tools.mkdir(parents=True)
        (source / 'tools/llvm-config').mkdir(parents=True)
        (source / 'tools/llvm-config/llvm-config.cpp').write_text('// patched upstream source fixture\n')
        strings = {
            'LLVM_SRC_ROOT': str(source), 'LLVM_OBJ_ROOT': str(build),
            'LLVM_CPPFLAGS': '-I' + str(source / 'include'),
            'LLVM_CFLAGS': '-I' + str(build / 'include') + ' -isystem ' + str(sysroot / 'usr/include'),
            'LLVM_CXXFLAGS': '-isystem' + str(source / 'include'),
            'LLVM_LDFLAGS': '-L' + str(build / 'lib') + ' -Wl,-R' + str(sysroot / 'usr/lib') + ' -Wl,-R' + str(sysroot / 'usr/pkg/lib'),
        }
        variables = ''.join('#define ' + key + ' ' + json.dumps(value) + '\n'
                            for key, value in strings.items())
        variables += '#define LLVM_HAS_RTTI 1\n#define LLVM_ENABLE_DYLIB 1\n#define LLVM_LINK_DYLIB 1\n'
        (tools / 'BuildVariables.inc').write_text(variables)
        (tools / 'LibraryDependencies.inc').write_text('fixture library table\n')
        (tools / 'ExtensionDependencies.inc').write_text('fixture extension table\n')
        cache = build / 'CMakeCache.txt'
        cache.write_text('CMAKE_SYSROOT:PATH=' + str(sysroot) + '\n')
        result = subprocess.run([sys.executable, '-B', str(script), str(tools), str(destination),
                                 str(source), str(build), str(cache)], capture_output=True, text=True)
        if result.returncode != 0:
            print('FAIL: metadata install failed: ' + result.stderr.strip())
            return 1
        output = (destination / 'BuildVariables.inc').read_text()
        for path in (str(source), str(build)):
            if path in output:
                print('FAIL: installed BuildVariables.inc retains ' + path)
                return 1
        if '"/__emberbsd_not_installed_source__"' not in output or \
                '"/__emberbsd_not_installed_build__"' not in output or \
                '-I/usr/pkg/include' not in output or '-L/usr/pkg/lib' not in output or \
                '-isystem /usr/include' not in output or \
                '-Wl,-R/usr/lib' not in output or \
                '-Wl,-R/usr/pkg/lib' not in output:
            print('FAIL: installed target paths were not normalized')
            return 1
        if not all((destination / name).is_file() for name in
                   ('LibraryDependencies.inc', 'ExtensionDependencies.inc', 'llvm-config.cpp')):
            print('FAIL: component tables were not installed')
            return 1
        if (destination / 'llvm-config.cpp').read_text() != '// patched upstream source fixture\n':
            print('FAIL: installed upstream source differs from WRKSRC')
            return 1
        # A same-version host llvm-config must still be rejected when it reports
        # a different target. This exercises the shared consumer validation.
        target = root / 'target'
        prefix = target / 'usr/pkg'
        config = prefix / 'lib/cmake/llvm/LLVMConfig.cmake'
        config.parent.mkdir(parents=True)
        config.write_text('set(LLVM_PACKAGE_VERSION 23.1.4)\n'
                          'set(LLVM_HOST_TRIPLE "aarch64--netbsd")\n'
                          'set(LLVM_TARGETS_TO_BUILD AArch64)\n'
                          'set(LLVM_ENABLE_ASSERTIONS OFF)\n')
        header = prefix / 'include/llvm/Config/llvm-config.h'
        header.parent.mkdir(parents=True)
        header.write_text('#define LLVM_VERSION_STRING "23.1.4"\n'
                          '#define LLVM_HOST_TRIPLE "aarch64--netbsd"\n'
                          '#define LLVM_DEFAULT_TARGET_TRIPLE "aarch64--netbsd"\n')
        metadata = prefix / 'lib/cmake/llvm/emberbsd'
        metadata.mkdir(parents=True)
        (metadata / 'BuildVariables.inc').write_text(
            '#define LLVM_SRC_ROOT "/__emberbsd_not_installed_source__"\n'
            '#define LLVM_OBJ_ROOT "/__emberbsd_not_installed_build__"\n'
            '#define LLVM_LDFLAGS "-L/usr/pkg/lib -Wl,-R/usr/pkg/lib"\n'
            '#define LLVM_HAS_RTTI 1\n#define LLVM_ENABLE_DYLIB 1\n#define LLVM_LINK_DYLIB 1\n')
        for name in ('LibraryDependencies.inc', 'ExtensionDependencies.inc', 'llvm-config.cpp'):
            (metadata / name).write_text('fixture\n')
        library = prefix / 'lib/libLLVM-23.so'
        library.parent.mkdir(parents=True, exist_ok=True)
        library.write_text('fixture library\n')
        def helper(path, *, version='23.1.4', triple='aarch64-unknown-netbsd',
                   reported_prefix=None, reported_root=None):
            reported_root = Path(reported_root or target).resolve()
            reported_prefix = Path(reported_prefix or reported_root / 'usr/pkg').resolve()
            reported_library = reported_prefix / 'lib/libLLVM-23.so'
            reported_flags = ('-L' + str(reported_prefix / 'lib') +
                              ' -L' + str(reported_root / 'usr/pkg/lib') +
                              ' -Wl,-R' + str(reported_root / 'usr/pkg/lib'))
            path.write_text('#!' + sys.executable + '\n'
                            'import sys\n'
                            'if "--libs" in sys.argv: print("-lLLVM-23")\n'
                            'elif "--libfiles" in sys.argv: print(' + repr(str(reported_library)) + ')\n'
                            'else: print("\\n".join([' + repr(version) + ', ' + repr(triple) + ', '
                            + repr(str(reported_prefix)) + ', ' + repr(str(reported_prefix / 'include')) + ', '
                            + repr(str(reported_prefix / 'lib')) + ', "AArch64", "OFF", "YES", '
                            + repr(reported_flags) + ', "shared"]))\n')
            path.chmod(0o755)
            return path

        def validate(candidate, root_path):
            return subprocess.run([sys.executable, '-B', '-c',
                                   'import sys; sys.path.insert(0, sys.argv[1]); '
                                   'from llvm_config_validation import validate_llvm_config; '
                                   'validate_llvm_config(sys.argv[2], sys.argv[3])',
                                   str(validator.parent), str(candidate), str(root_path)],
                                  capture_output=True, text=True)

        current_good = validate(helper(root / 'current-llvm-config'), target)
        if current_good.returncode != 0:
            print('FAIL: helper matching the installed target was rejected: ' + current_good.stderr.strip())
            return 1
        wrong_target = validate(helper(root / 'wrong-target-llvm-config',
                                       triple='x86_64-apple-darwin'), target)
        if wrong_target.returncode == 0 or 'does not match the installed target LLVM metadata' not in wrong_target.stderr:
            print('FAIL: same-version llvm-config with the wrong target was accepted')
            return 1
        wrong_version = validate(helper(root / 'wrong-version-llvm-config', version='23.1.5'), target)
        if wrong_version.returncode == 0 or 'does not match the installed target LLVM metadata' not in wrong_version.stderr:
            print('FAIL: llvm-config with the wrong version was accepted')
            return 1
        wrong_prefix = validate(helper(root / 'wrong-prefix-llvm-config',
                                       reported_prefix=root / 'elsewhere/usr/pkg'), target)
        if wrong_prefix.returncode == 0 or 'does not match the installed target LLVM metadata' not in wrong_prefix.stderr:
            print('FAIL: llvm-config reporting another installed prefix was accepted')
            return 1
        relocated = root / 'relocated'
        shutil.copytree(target, relocated)
        relocated_new = validate(helper(root / 'relocated-llvm-config',
                                        reported_prefix=relocated / 'usr/pkg',
                                        reported_root=relocated.resolve()), relocated)
        if relocated_new.returncode != 0:
            print('FAIL: helper rebuilt for the relocated prefix was rejected: ' + relocated_new.stderr.strip())
            return 1
        relocated_old = validate(helper(root / 'old-prefix-llvm-config'), relocated)
        if relocated_old.returncode == 0 or 'does not match the installed target LLVM metadata' not in relocated_old.stderr:
            print('FAIL: helper retaining the old prefix was accepted after sysroot relocation')
            return 1

        host_prefix = root / 'host prefix'
        host_config = host_prefix / 'bin/llvm-config'
        host_config.parent.mkdir(parents=True)
        host_config.write_text('#!' + sys.executable + '\nprint("23.1.4")\n')
        host_config.chmod(0o755)
        host_cpp = host_prefix / 'bin/clang++'
        native_ld = host_prefix / 'bin/ld.lld'
        host_cpp.write_text('#!' + sys.executable + '\n')
        native_ld.write_text('#!' + sys.executable + '\n')
        host_cpp.chmod(0o755)
        native_ld.chmod(0o755)
        producer = Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files/build-installed-llvm-config.py'

        def compile_refusal(native_cxx, native_linker, expected):
            result = subprocess.run([sys.executable, '-B', '-c',
                                     'import importlib.util, sys; p=sys.argv[1]; '
                                     'sys.path.insert(0, str(__import__("pathlib").Path(p).parent)); '
                                     's=importlib.util.spec_from_file_location("producer", p); '
                                     'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                                     'm.compile_helper(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])',
                                     str(producer), str(root / 'helper/bin/llvm-config'),
                                     str(root / 'helper-work'), str(target), str(host_prefix)],
                                    env={**os.environ, 'NATIVE_CXX': str(native_cxx),
                                         'EMBERBSD_NATIVE_LD': str(native_linker)},
                                    capture_output=True, text=True)
            return result.returncode != 0 and expected in result.stderr

        if not compile_refusal(sys.executable, native_ld,
                               'NATIVE_CXX must come from the selected host prefix'):
            print('FAIL: installed producer accepted a native compiler outside its prefix')
            return 1
        if not compile_refusal(host_cpp, sys.executable,
                               'EMBERBSD_NATIVE_LD must come from the selected host prefix'):
            print('FAIL: installed producer accepted a native linker outside its prefix')
            return 1

        for path in (host_cpp, native_ld, host_prefix / 'include/llvm/Config/llvm-config.h',
                     *(host_prefix / 'lib' / ('lib' + name + '.a') for name in
                       ('LLVMSupport', 'LLVMTargetParser', 'LLVMDemangle'))):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture input\n')
        spec = spec_from_file_location('installed_llvm_config', producer)
        sys.path.insert(0, str(producer.parent))
        installed_producer = module_from_spec(spec)
        spec.loader.exec_module(installed_producer)
        os.environ['NATIVE_CXX'] = str(host_cpp)
        os.environ['EMBERBSD_NATIVE_LD'] = str(native_ld)
        # Exercise the producer's real compile invocation with a recording compiler.
        (metadata / 'llvm-config.cpp').write_text(
            'using namespace llvm;\nCurrentExecPrefix =\n'
            '      sys::path::parent_path(sys::path::parent_path(CurrentPath)).str();\n'
            '#if defined(NDEBUG)\n#endif\n')
        recorded = []
        def fake_capture(argv):
            if '--version' in argv:
                return '23.1.4'
            if '--libfiles' in argv:
                return ' '.join(__import__('shlex').quote(str(host_prefix.resolve() / 'lib' / ('lib' + name + '.a'))) for name in ('LLVMSupport', 'LLVMTargetParser', 'LLVMDemangle'))
            return ''
        def fake_run(argv, **kwargs):
            recorded.append(argv)
            Path(argv[argv.index('-o') + 1]).write_text('helper')
        installed_producer.capture = fake_capture
        installed_producer.subprocess.run = fake_run
        installed_producer.validate_llvm_config = lambda *args: None
        installed_producer.compile_helper(str(root / 'unused'), str(root / 'compile-work'), str(target), str(host_prefix))
        expected_flags = ['-Xlinker', '-rpath', '-Xlinker', str(host_prefix.resolve() / 'lib')]
        if not any(command[i:i+4] == expected_flags for command in recorded for i in range(len(command))):
            print('FAIL: compiler invocation lacks selected native runtime path')
            return 1
        first_key = installed_producer.cache_key(target, host_prefix)
        expected_flags = ['-Xlinker', '-rpath', '-Xlinker', str(host_prefix.resolve() / 'lib')]
        if installed_producer.native_runtime_flags(host_prefix.resolve()) != expected_flags or first_key['native_runtime_flags'] != expected_flags:
            print('FAIL: helper runtime path missing from link flags or cache key')
            return 1
        if first_key != installed_producer.cache_key(target, host_prefix):
            print('FAIL: unchanged installed LLVM inputs did not retain their cache identity')
            return 1
        (metadata / 'LibraryDependencies.inc').write_text('changed installed table\n')
        if first_key == installed_producer.cache_key(target, host_prefix):
            print('FAIL: changed installed LLVM metadata retained its cache identity')
            return 1
    print('PASS: installed metadata normalization, target/version/prefix/host/relocation checks and cache invalidation')
    return 0


if __name__ == '__main__':
    sys.exit(main())
