#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that installed target llvm-config tables do not retain build paths."""
import json
from pathlib import Path
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
        header.write_text('#define LLVM_HOST_TRIPLE "aarch64--netbsd"\n'
                          '#define LLVM_DEFAULT_TARGET_TRIPLE "aarch64--netbsd"\n')
        metadata = prefix / 'lib/cmake/llvm/emberbsd'
        metadata.mkdir(parents=True)
        (metadata / 'BuildVariables.inc').write_text(
            '#define LLVM_LDFLAGS "-L/usr/pkg/lib -Wl,-R/usr/pkg/lib"\n'
            '#define LLVM_HAS_RTTI 1\n')
        for name in ('LibraryDependencies.inc', 'ExtensionDependencies.inc', 'llvm-config.cpp'):
            (metadata / name).write_text('fixture\n')
        library = prefix / 'lib/libLLVM-23.so'
        library.parent.mkdir(parents=True, exist_ok=True)
        library.write_text('fixture library\n')
        helper = root / 'wrong-target-llvm-config'
        helper.write_text('#!' + sys.executable + '\n'
                          'import sys\n'
                          'if "--libs" in sys.argv: print("-lLLVM-23")\n'
                          'elif "--libfiles" in sys.argv: print(' + repr(str(library)) + ')\n'
                          'else: print("\\n".join(['
                          '"23.1.4", "x86_64-apple-darwin", ' + repr(str(prefix)) + ', '
                          + repr(str(prefix / 'include')) + ', ' + repr(str(prefix / 'lib')) + ', '
                          '"AArch64", "OFF", "YES", '
                          + repr('-L' + str(prefix / 'lib') + ' -L' + str(prefix / 'lib') +
                                 ' -Wl,-R' + str(prefix / 'lib')) + ', "shared"]))\n')
        helper.chmod(0o755)
        check = subprocess.run([sys.executable, '-B', '-c',
                                'import sys; sys.path.insert(0, sys.argv[1]); '
                                'from llvm_config_validation import validate_llvm_config; '
                                'validate_llvm_config(sys.argv[2], sys.argv[3])',
                                str(validator.parent), str(helper), str(target)],
                               capture_output=True, text=True)
        if check.returncode == 0 or 'does not match the installed target LLVM metadata' not in check.stderr:
            print('FAIL: same-version llvm-config with the wrong target was accepted')
            return 1
    print('PASS: installed llvm-config tables use package paths and preserve component tables')
    return 0


if __name__ == '__main__':
    sys.exit(main())
