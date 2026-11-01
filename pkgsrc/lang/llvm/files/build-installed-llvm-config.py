#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build-host llvm-config from installed package inputs.
"""Compile upstream llvm-config.cpp from installed target/native package metadata."""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from llvm_config_validation import target_ldflags, validate_llvm_config

VERSION = '23.1.4'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def capture(argv):
    result = subprocess.run(argv, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def definitions(path):
    return {m[1]: m[2].strip() for line in Path(path).read_text().splitlines()
            if (m := re.fullmatch(r'#define ([A-Z][A-Z0-9_]*) (.+)', line))}


def string(values, name):
    result = json.loads(values[name])
    require(isinstance(result, str), 'unsupported target macro ' + name)
    return result


def set_macro(text, name, value):
    pattern = r'^#define ' + re.escape(name) + r' .+$'
    text, count = re.subn(pattern, '#define ' + name + ' ' + json.dumps(value), text, count=1, flags=re.M)
    require(count == 1, 'target BuildVariables is missing ' + name)
    return text




def compile_helper(config, work, sysroot, host_prefix):
    config = Path(config)
    work = Path(work)
    sysroot = Path(sysroot).resolve(strict=True)
    host_prefix = Path(host_prefix).resolve(strict=True)
    target_prefix = sysroot / 'usr/pkg'
    require((target_prefix / 'lib/cmake/llvm/LLVMConfig.cmake').is_file(), 'target llvm-devel is not installed')
    require((target_prefix / 'lib/libLLVM-23.so').is_file(), 'target shared LLVM is not installed')
    target_version = re.search(r'^set\(LLVM_PACKAGE_VERSION\s+([^ )]+)\)',
                               (target_prefix / 'lib/cmake/llvm/LLVMConfig.cmake').read_text(), re.M)
    require(target_version and target_version[1] == VERSION, 'installed target LLVM version mismatch')
    cmake_config = (target_prefix / 'lib/cmake/llvm/LLVMConfig.cmake').read_text()
    metadata = target_prefix / 'lib/cmake/llvm/emberbsd'
    variables_path = metadata / 'BuildVariables.inc'
    tables = [metadata / name for name in ('LibraryDependencies.inc', 'ExtensionDependencies.inc')]
    require(variables_path.is_file() and all(path.is_file() for path in tables),
            'installed target llvm-config metadata is missing')
    target_header = definitions(target_prefix / 'include/llvm/Config/llvm-config.h')
    require(string(target_header, 'LLVM_VERSION_STRING') == VERSION, 'installed target header version mismatch')
    cmake_triple = re.search(r'^set\(LLVM_HOST_TRIPLE\s+"([^"]+)"\)', cmake_config, re.M)
    cmake_targets = re.search(r'^set\(LLVM_TARGETS_TO_BUILD\s+([^)]*)\)', cmake_config, re.M)
    require(cmake_triple and cmake_triple[1] == string(target_header, 'LLVM_HOST_TRIPLE') and
            cmake_triple[1] == string(target_header, 'LLVM_DEFAULT_TARGET_TRIPLE'),
            'installed target triple metadata disagrees')
    require(cmake_targets is not None, 'installed LLVM CMake config lacks built target metadata')
    variables = definitions(variables_path)
    require(string(variables, 'LLVM_OBJ_ROOT') == '/__emberbsd_not_installed_build__' and
            string(variables, 'LLVM_SRC_ROOT') == '/__emberbsd_not_installed_source__',
            'installed metadata still names a CMake source/build tree')
    for key in ('LLVM_ENABLE_DYLIB', 'LLVM_LINK_DYLIB', 'LLVM_HAS_RTTI'):
        require(variables.get(key) == '1', 'unsupported installed LLVM setting: ' + key)
    target_linker_flags = target_ldflags(variables, sysroot)

    host_config = host_prefix / 'bin/llvm-config'
    require(host_config.is_file() and os.access(host_config, os.X_OK), 'native llvm-config is missing')
    require(capture([str(host_config), '--version']) == VERSION, 'native LLVM version mismatch')
    cxx = Path(os.environ.get('NATIVE_CXX', str(host_prefix / 'bin/clang++'))).resolve(strict=True)
    require(cxx.is_relative_to(host_prefix) and os.access(cxx, os.X_OK), 'NATIVE_CXX must come from the selected host prefix')
    native_ld = Path(os.environ.get('EMBERBSD_NATIVE_LD', '')).resolve(strict=True)
    require(native_ld.is_relative_to(host_prefix) and os.access(native_ld, os.X_OK),
            'EMBERBSD_NATIVE_LD must come from the selected host prefix')
    cxxflags = shlex.split(capture([str(host_config), '--cxxflags']))
    host_ldflags = shlex.split(capture([str(host_config), '--ldflags']))
    libraries = shlex.split(capture([str(host_config), '--link-static', '--libfiles',
                                     'support', 'targetparser', 'demangle']))
    system_libraries = shlex.split(capture([str(host_config), '--link-static', '--system-libs',
                                            'support', 'targetparser', 'demangle']))
    expected = [str(host_prefix / 'lib' / ('lib' + name + '.a')) for name in
                ('LLVMSupport', 'LLVMTargetParser', 'LLVMDemangle')]
    require(sorted(libraries) == sorted(expected) and all(Path(path).is_file() for path in libraries),
            'native static LLVM Support closure is incomplete')

    helper = work / 'helper/bin/llvm-config'
    helper.parent.mkdir(parents=True)
    (work / 'metadata').mkdir()
    for path in [variables_path, *tables, metadata / 'llvm-config.cpp']:
        (work / 'metadata' / path.name).write_bytes(path.read_bytes())
    variables_work = work / 'metadata/BuildVariables.inc'
    text = variables_work.read_text()
    text = set_macro(text, 'LLVM_LDFLAGS', target_linker_flags)
    # The installed tool must select the installed-prefix path, never a stale CMake tree.
    text = set_macro(text, 'LLVM_SRC_ROOT', '/__emberbsd_not_installed_source__')
    text = set_macro(text, 'LLVM_OBJ_ROOT', '/__emberbsd_not_installed_build__')
    variables_work.write_text(text)

    (work / 'host-config/llvm/Config').mkdir(parents=True)
    # llvm-config.cpp uses config.h here only for PACKAGE_VERSION; this tiny
    # host-side shim takes the value from installed target LLVMConfig.cmake.
    version_macro = json.dumps(target_version[1])
    (work / 'host-config/llvm/Config/config.h').write_text('#define PACKAGE_VERSION ' + version_macro + '\n')
    cpp = (metadata / 'llvm-config.cpp').read_text()
    assertions = re.search(r'^set\(LLVM_ENABLE_ASSERTIONS\s+(ON|OFF)\)', cmake_config, re.M)
    require(assertions is not None, 'installed LLVM CMake config lacks LLVM_ENABLE_ASSERTIONS')
    report = '\n'.join('#undef ' + name + '\n#define ' + name + ' ' + target_header[name]
                       for name in ('LLVM_HOST_TRIPLE', 'LLVM_DEFAULT_TARGET_TRIPLE'))
    report += '\n#define EMBER_TARGET_ASSERTIONS ' + ('1' if assertions[1] == 'ON' else '0') + '\n'
    anchor = 'using namespace llvm;'
    require(cpp.count(anchor) == 1, 'upstream llvm-config source context changed')
    cpp = cpp.replace(anchor, report + '\n' + anchor, 1)
    prefix_line = ('CurrentExecPrefix =\n'
                   '      sys::path::parent_path(sys::path::parent_path(CurrentPath)).str();')
    require(cpp.count(prefix_line) == 1, 'upstream llvm-config relocation context changed')
    cpp = cpp.replace(prefix_line, 'CurrentExecPrefix = ' + json.dumps(str(target_prefix)) + ';', 1)
    require(cpp.count('#if defined(NDEBUG)') == 1, 'upstream assertion-mode context changed')
    cpp = cpp.replace('#if defined(NDEBUG)', '#if !EMBER_TARGET_ASSERTIONS', 1)
    source = work / 'llvm-config.cpp'
    source.write_text(cpp)

    host_flags = shlex.split(os.environ.get('NATIVE_CXXFLAGS', '')) + cxxflags
    host_ldflags += shlex.split(os.environ.get('NATIVE_LDFLAGS', ''))
    if native_ld.name == 'ld.lld':
        host_ldflags.append('-fuse-ld=lld')
    else:
        host_ldflags.append('-B' + str(native_ld.parent) + os.sep)
    output = work / 'helper/bin/llvm-config'
    command = [str(cxx), '-I' + str(work / 'host-config'),
               '-I' + str(work / 'metadata'),
               *host_flags, '-DLLVM_BUILD_STATIC', '-O2', '-DNDEBUG',
               str(source), *host_ldflags, *libraries, *system_libraries, '-o', str(output)]
    subprocess.run(command, check=True)
    output.chmod(0o755)
    validate_llvm_config(output, sysroot)
    print(str(output))


def main(argv):
    if len(argv) != 4:
        raise SystemExit('usage: build-installed-llvm-config.py CONFIG WORK SYSROOT HOST_PREFIX')
    config, work, sysroot, host_prefix = argv
    require(Path(config) == Path(work) / 'helper/bin/llvm-config',
            'helper output must be WORK/helper/bin/llvm-config')
    key = cache_key(sysroot, host_prefix)
    work = Path(work)
    if work.is_dir() and os.access(config, os.X_OK):
        try:
            previous = json.loads((work / 'cache-key.json').read_text())
            if previous == key:
                validate_llvm_config(config, sysroot)
                print('use ' + config)
                return 0
        except (OSError, ValueError, subprocess.CalledProcessError):
            pass
    work.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.' + work.name + '.new-', dir=work.parent))
    try:
        compile_helper(str(stage / 'helper/bin/llvm-config'), stage, sysroot, host_prefix)
        (stage / 'cache-key.json').write_text(json.dumps(key, sort_keys=True) + '\n')
        old = None
        if work.exists():
            old = work.with_name(work.name + '.previous-' + str(os.getpid()))
            os.replace(work, old)
        try:
            os.replace(stage, work)
        except BaseException:
            if old is not None:
                os.replace(old, work)
            raise
        if old is not None:
            try:
                shutil.rmtree(old)
            except OSError as error:
                print('build-installed-llvm-config: old helper work retained at ' + str(old) + ': ' + str(error),
                      file=sys.stderr)
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    return 0


def cache_key(sysroot, host_prefix):
    sysroot = Path(sysroot).resolve(strict=True)
    host_prefix = Path(host_prefix).resolve(strict=True)
    target = sysroot / 'usr/pkg'
    compiler = Path(os.environ.get('NATIVE_CXX', str(host_prefix / 'bin/clang++'))).resolve(strict=True)
    linker = Path(os.environ['EMBERBSD_NATIVE_LD']).resolve(strict=True)
    paths = [target / 'lib/cmake/llvm/LLVMConfig.cmake',
             target / 'include/llvm/Config/llvm-config.h', target / 'lib/libLLVM-23.so',
             target / 'lib/cmake/llvm/emberbsd/BuildVariables.inc',
             target / 'lib/cmake/llvm/emberbsd/LibraryDependencies.inc',
             target / 'lib/cmake/llvm/emberbsd/ExtensionDependencies.inc',
             target / 'lib/cmake/llvm/emberbsd/llvm-config.cpp',
             host_prefix / 'bin/llvm-config', compiler, linker, host_prefix / 'include/llvm/Config/llvm-config.h',
             *[host_prefix / 'lib' / ('lib' + name + '.a') for name in
               ('LLVMSupport', 'LLVMTargetParser', 'LLVMDemangle')]]
    identities = []
    for path in paths:
        try:
            stat = path.stat()
        except OSError as error:
            raise ValueError('required llvm-config input is unavailable: ' + str(path)) from error
        require(path.is_file(), 'llvm-config input is not a regular file: ' + str(path))
        identities.append(dict(path=str(path.resolve()), dev=stat.st_dev, ino=stat.st_ino,
                                size=stat.st_size, mtime_ns=stat.st_mtime_ns, ctime_ns=stat.st_ctime_ns))
    return dict(version=VERSION, sysroot=str(sysroot), host_prefix=str(host_prefix),
                native_cxx=str(compiler), native_ld=str(linker),
                native_cxxflags=os.environ.get('NATIVE_CXXFLAGS', ''),
                native_ldflags=os.environ.get('NATIVE_LDFLAGS', ''), inputs=identities)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('build-installed-llvm-config: ' + str(error), file=sys.stderr)
        sys.exit(1)
