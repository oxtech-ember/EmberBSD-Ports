#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compile upstream's real metadata interpreter.
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
sys.dont_write_bytecode = True
import llvm_sdk as sdk
import llvm_target as target_api
import llvm_native as native_api

UPSTREAM_SHA256 = '7c54727d9deda1689a7e6c9096f6627d73659da04a6ac88c3e0a0595f26e74bb'
VERSION = '23.1.4'
LOCAL = ['metadata/BuildVariables.inc', 'metadata/LibraryDependencies.inc', 'metadata/ExtensionDependencies.inc',
         'llvm-config.cpp', 'build-llvm-config.py', 'llvm_target.py', 'llvm_native.py', 'llvm_sdk.py',
         'llvm-config.d', 'dependencies.command', 'compile.command', 'receipt.json', 'bin/llvm-config.real', 'bin/llvm-config']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cache(path):
    return {m[1]: m[2].strip() for line in Path(path).read_text().splitlines()
            if (m := re.fullmatch(r'([^#/][^:=]*):[^=]+=(.*)', line))}


def definitions(path):
    return {m[1]: m[2].strip() for line in Path(path).read_text().splitlines()
            if (m := re.fullmatch(r'#define ([A-Z][A-Z0-9_]*) (.+)', line))}


def string(defs, key):
    value = json.loads(defs[key])
    require(isinstance(value, str), 'missing or unsupported C string ' + key)
    return value


def replace_once(text, old, replacement):
    require(text.count(old) == 1, 'upstream context changed: ' + old.splitlines()[0])
    return text.replace(old, replacement, 1)


def build(args):
    from emberbsd_sdk.process import ContextLocks
    require(len(args) == 6, 'usage: build-llvm-config.py --sdk-source SDK LLVM_SOURCE TARGET_BUILD NATIVE_BUILD SYSROOT TARGET_PREFIX NEW_WORK')
    source, target, native, sysroot, prefix = [sdk.existing_directory(p) for p in args[:5]]
    destination = sdk.new_destination(args[5], (source, target, native, sysroot, prefix))
    # The lock covers preflight, every producer, stable input verification and publication.
    with ContextLocks([destination], str(Path(destination).parent)):
        sdk.new_destination(destination, (source, target, native, sysroot, prefix))
        return build_locked(source, target, native, sysroot, prefix, destination)


def build_locked(source, target, native, sysroot, prefix, destination):
    sdk_root = sdk.sdk_source.load()
    from emberbsd_sdk.provenance import git_source
    sdk_provenance = git_source(sdk_root, env=sdk.environment())
    sdk_inputs = {str(p): sdk.digest(p) for p in sorted((Path(sdk_root) / 'src/emberbsd_sdk').glob('*.py'))}
    sdk_inputs[str(Path(sdk.sdk_source.__file__).resolve())] = sdk.digest(sdk.sdk_source.__file__)
    sdk_inputs[str(Path(sys.executable).resolve())] = sdk.digest(sys.executable)
    producer_inputs = {name: sdk.digest(Path(__file__).parent / name) for name in ('build-llvm-config.py', 'llvm_target.py', 'llvm_native.py', 'llvm_sdk.py')}
    cpp = source + '/tools/llvm-config/llvm-config.cpp'
    require(Path(cpp).is_file() and sdk.digest(cpp) == UPSTREAM_SHA256, 'upstream llvm-config.cpp differs from LLVM 23.1.4')
    required = [cpp]
    for root in (target, native):
        required += [root + '/' + p for p in ('CMakeCache.txt', 'include/llvm/Config/llvm-config.h', 'include/llvm/Config/config.h', 'include/llvm/Config/abi-breaking.h')]
    required += [target + '/tools/llvm-config/' + p for p in ('BuildVariables.inc', 'LibraryDependencies.inc', 'ExtensionDependencies.inc')]
    for path in required:
        require(Path(path).is_file(), 'missing input: ' + path)
    hashes = {p: sdk.digest(p) for p in required}
    tc, nc = cache(target + '/CMakeCache.txt'), cache(native + '/CMakeCache.txt')
    td, nd = [definitions(root + '/include/llvm/Config/llvm-config.h') for root in (target, native)]
    config = definitions(target + '/include/llvm/Config/config.h')
    variables = definitions(target + '/tools/llvm-config/BuildVariables.inc')
    require(tc.get('CMAKE_SYSTEM_NAME') == 'NetBSD' and tc.get('CMAKE_SYSTEM_PROCESSOR') in ('aarch64', 'x86_64'), 'target must be configured for NetBSD/aarch64 or NetBSD/x86_64')
    require(tc.get('CMAKE_SYSROOT') and sdk.existing_directory(tc['CMAKE_SYSROOT']) == sysroot, 'supplied sysroot differs from the target configuration')
    require(all(string(d, 'LLVM_VERSION_STRING') == VERSION for d in (td, nd)), 'target and native LLVM versions must both be 23.1.4')
    require(string(config, 'PACKAGE_VERSION') == string(td, 'LLVM_VERSION_STRING'), 'target PACKAGE_VERSION disagrees with LLVM_VERSION_STRING')
    require(sdk.existing_directory(nc['CMAKE_HOME_DIRECTORY']) == source, 'native source does not match the supplied source tree')
    require(string(variables, 'LLVM_OBJ_ROOT') == target, 'target object root does not match TARGET_BUILD')
    require(string(variables, 'LLVM_SRC_ROOT') == tc['CMAKE_HOME_DIRECTORY'], 'target source root does not match its CMake cache')
    target_cpp = tc['CMAKE_HOME_DIRECTORY'] + '/tools/llvm-config/llvm-config.cpp'
    require(Path(target_cpp).is_file() and sdk.digest(target_cpp) == UPSTREAM_SHA256, 'target llvm-config source differs from the pinned upstream source')
    required.append(target_cpp)
    hashes[target_cpp] = sdk.digest(target_cpp)
    for key in ('LLVM_ENABLE_DYLIB', 'LLVM_LINK_DYLIB', 'LLVM_HAS_RTTI'):
        require(variables.get(key) == '1', 'target requires ' + key + '=1')
    require(all(tc.get(k) == 'ON' for k in ('LLVM_BUILD_LLVM_DYLIB', 'LLVM_LINK_LLVM_DYLIB', 'LLVM_ENABLE_RTTI')), 'target shared LLVM/RTTI cache disagrees with generated metadata')
    require(tc.get('CMAKE_INSTALL_PREFIX') == '/usr/pkg' and string(variables, 'LLVM_INSTALL_INCLUDEDIR') == 'include' and not string(variables, 'LLVM_LIBDIR_SUFFIX'), 'only the canonical /usr/pkg install layout is supported')
    require(tc.get('LLVM_ENABLE_ASSERTIONS') in ('ON', 'OFF'), 'unsupported target assertion mode')
    require(nc.get('LLVM_ENABLE_ASSERTIONS') in ('ON', 'OFF'), 'native assertion mode must be explicit')
    spec = target_api.validate(tc, td, Path(target + '/tools/llvm-config/LibraryDependencies.inc').read_text())
    library_hash = proof = None
    if prefix != target:
        for name in ('llvm-config.h', 'abi-breaking.h'):
            staged = prefix + '/include/llvm/Config/' + name
            generated = target + '/include/llvm/Config/' + name
            require(Path(staged).is_file() and Path(staged).read_bytes() == Path(generated).read_bytes(), 'staged target header missing or mismatched: ' + name)
            required.append(staged)
            hashes[staged] = sdk.digest(staged)
        library, built_library = prefix + '/lib/libLLVM-23.so', target + '/lib/libLLVM.so'
        require(Path(library).is_file() and Path(built_library).is_file(), 'staged shared LLVM or its original target build output is missing')
        require(str(Path(library).resolve(strict=True)).startswith(prefix + '/lib/'), 'staged shared LLVM resolves outside the target prefix')
        target_api.validate_elf(library, spec)
        library_hash, built_hash = sdk.digest(library), sdk.digest(built_library)
        proof = dict(method='identical', built_library=built_library, built_sha256=built_hash, staged_library=library, staged_sha256=library_hash)
        if library_hash != built_hash:
            strip = tc.get('CMAKE_STRIP', '')
            require(strip.startswith('/') and os.access(strip, os.X_OK), 'CMAKE_STRIP must be an absolute executable')
            install_script = target + '/tools/llvm-shlib/cmake_install.cmake'
            require(Path(install_script).is_file(), 'missing shared LLVM install script')
            script = Path(install_script).read_text()
            installed = '$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/' + Path(built_library).resolve(strict=True).name
            invocation = 'execute_process(COMMAND "' + strip + '" "' + installed + '")'
            block = 'if(CMAKE_INSTALL_DO_STRIP)\n      ' + invocation + '\n    endif()'
            install = 'file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE SHARED_LIBRARY FILES "' + str(Path(built_library).resolve(strict=True)) + '")'
            require(script.count(block) == 1 and script.count(install) == 1 and [v.strip() for v in re.findall(r'execute_process\([^\n]*', script)] == [invocation] and not re.search(r'RPATH_(?:CHANGE|REMOVE)', script), 'unsupported shared LLVM install/strip transformation')
            proof.update(method='cmake-install-strip', strip=strip, strip_version=sdk.capture(strip, '--version'), install_script=install_script)
            required += [strip, install_script]
        required += [library, built_library]
        for p in required:
            hashes.setdefault(p, sdk.digest(p))
    host_config = native + '/bin/llvm-config'
    require(os.access(host_config, os.X_OK), 'missing runnable native llvm-config')
    hashes[host_config] = sdk.digest(host_config)
    require(sdk.capture(host_config, '--version') == VERSION, 'native llvm-config version mismatch')
    native_triple = sdk.capture(host_config, '--host-target')
    native_platform = native_api.platform(native_triple)
    host_flags = shlex.split(sdk.capture(host_config, '--cxxflags'))
    host_ldflags = shlex.split(sdk.capture(host_config, '--ldflags'))
    host_libs = shlex.split(sdk.capture(host_config, '--link-static', '--libfiles', 'support', 'targetparser'))
    expected_libs = [native + '/lib/lib' + name + '.a' for name in ('LLVMSupport', 'LLVMTargetParser', 'LLVMDemangle')]
    require(sorted(host_libs) == sorted(expected_libs), 'native Support library closure differs from the supported minimal closure')
    host_system = shlex.split(sdk.capture(host_config, '--link-static', '--system-libs', 'support', 'targetparser'))
    if native_platform == 'darwin':
        require(host_system == ['-lm'], 'unexpected native system library requirements')
    else:
        for arg in host_system:
            require((re.fullmatch(r'-l[A-Za-z0-9_+.-]+', arg) and not arg.startswith('-lLLVM')) or (arg.startswith('/') and Path(arg).is_file() and re.search(r'\.(?:a|so(?:\.[0-9]+)*)$', arg) and not Path(arg).name.startswith('libLLVM')), 'unsupported native system library argument')
    cxx = os.environ.get('NATIVE_CXX') or nc['CMAKE_CXX_COMPILER']
    require(cxx.startswith('/') and os.access(cxx, os.X_OK), 'native C++ compiler must be an existing absolute executable')
    native_sdk, native_headers, compiler_runtime = None, [], []
    if native_platform == 'darwin':
        native_sdk = sdk.existing_directory(nc.get('CMAKE_OSX_SYSROOT') or sdk.capture('/usr/bin/xcrun', '--show-sdk-path'))
        host_flags += ['-isysroot', native_sdk]
        if nc.get('CMAKE_OSX_DEPLOYMENT_TARGET'):
            host_flags.append('-mmacosx-version-min=' + nc['CMAKE_OSX_DEPLOYMENT_TARGET'])
        native_headers = [native_sdk]
    else:
        measured = native_api.compiler(cxx, native_triple, host_flags)
        native_headers, compiler_runtime = measured['header_roots'], measured['compiler_libraries']
        require(not any(path == root or path.startswith(root + '/') for path in native_headers for root in (sysroot, target)), 'native include search enters a target tree')
    required += [host_config, cxx, *host_libs, *(a for a in host_system if a.startswith('/'))]
    for p in required:
        hashes.setdefault(p, sdk.digest(p))
    original_ldflags = string(variables, 'LLVM_LDFLAGS')
    mapped = []
    for flag in shlex.split(original_ldflags):
        if flag.startswith('-L/'):
            path = flag[2:]
            require(not (path == sysroot or path.startswith(sysroot + '/')), 'target LLVM_LDFLAGS leaks CMAKE_SYSROOT; fix target metadata before building this tool')
            require(any(path == p or path.startswith(p + '/') for p in ('/usr/lib', '/usr/pkg', '/lib')), 'unmapped library search path: ' + path)
            flag = '-L' + sysroot + path
        elif flag.startswith('-L') or re.search(r'\s', flag):
            raise ValueError('unsupported target linker flag: ' + flag)
        elif any(p in flag for p in (source, target, native, sysroot)):
            raise ValueError('build path outside a library search flag: ' + flag)
        mapped.append(flag)
    mapped_ldflags = ' '.join(mapped)
    # All preflight above is read-only. Failed producers retain this unique partial path.
    work = sdk.stage_for(destination)
    work_root = str(Path(work).resolve(strict=True))
    print('Retained partial work on failure: ' + work, file=sys.stderr, flush=True)
    (Path(work) / 'metadata').mkdir()
    (Path(work) / 'bin').mkdir()
    if proof and proof['method'] == 'cmake-install-strip':
        copied = Path(work) / 'strip-check.so'
        shutil.copyfile(proof['built_library'], copied)
        require(sdk.digest(copied) == proof['built_sha256'], 'shared LLVM copy differs before stripping')
        command = [proof['strip'], str(copied)]
        sdk.command_file(Path(work) / 'strip.command', command)
        sdk.produce(command, Path(work) / 'strip.log')
        proof['reproduced_sha256'] = sdk.digest(copied)
        require(proof['reproduced_sha256'] == library_hash, 'staged shared LLVM differs from the reproduced CMake install-strip output')
        copied.unlink()
    for name in ('BuildVariables.inc', 'LibraryDependencies.inc', 'ExtensionDependencies.inc'):
        shutil.copyfile(target + '/tools/llvm-config/' + name, Path(work) / 'metadata' / name)
    path = Path(work) / 'metadata/BuildVariables.inc'
    path.write_text(replace_once(path.read_text(), '#define LLVM_LDFLAGS ' + variables['LLVM_LDFLAGS'], '#define LLVM_LDFLAGS ' + json.dumps(mapped_ldflags)))
    report = '\n'.join('#undef ' + key + '\n#define ' + key + ' ' + td[key] for key in ('LLVM_HOST_TRIPLE', 'LLVM_DEFAULT_TARGET_TRIPLE'))
    report += '\n#undef PACKAGE_VERSION\n#define PACKAGE_VERSION ' + config['PACKAGE_VERSION'] + '\n'
    report += '#define EMBER_TARGET_ASSERTIONS ' + ('1' if tc['LLVM_ENABLE_ASSERTIONS'] == 'ON' else '0') + '\n'
    text = replace_once(Path(cpp).read_text(), 'using namespace llvm;', '// EmberBSD: report target facts after parsing coherent native headers.\n' + report + '\nusing namespace llvm;')
    text = replace_once(text, 'CurrentExecPrefix =\n      sys::path::parent_path(sys::path::parent_path(CurrentPath)).str();', 'CurrentExecPrefix = ' + json.dumps(prefix) + '; // EmberBSD target prefix')
    text = replace_once(text, '#if defined(NDEBUG)', '#if !EMBER_TARGET_ASSERTIONS')
    (Path(work) / 'llvm-config.cpp').write_text(text)
    for name in ('build-llvm-config.py', 'llvm_target.py', 'llvm_native.py', 'llvm_sdk.py'):
        shutil.copyfile(Path(__file__).parent / name, Path(work) / name)
        require(sdk.digest(Path(work) / name) == producer_inputs[name], 'producer source changed while copying: ' + name)
    compile_args = [cxx, *host_flags, '-DLLVM_BUILD_STATIC', '-O2', '-DNDEBUG' if nc['LLVM_ENABLE_ASSERTIONS'] == 'OFF' else '-UNDEBUG', '-I' + work + '/metadata', work + '/llvm-config.cpp']
    mode = ['-M'] if native_platform == 'linux-gnu' else ['-MM']
    if native_platform == 'linux-gnu' and measured['family'] == 'gcc':
        mode.insert(0, '-fno-canonical-system-headers')
    dependency_command = [*compile_args, *mode, '-MT', 'llvm-config', '-MF', work + '/llvm-config.d']
    sdk.command_file(Path(work) / 'dependencies.command', dependency_command)
    sdk.produce(dependency_command, Path(work) / 'dependencies.log')
    dependencies = shlex.split(re.sub(r'^llvm-config:\s*', '', (Path(work) / 'llvm-config.d').read_text().replace('\\\n', ' ')))
    for path in dependencies:
        path = native_api.validate_header(path, [work, source, native, *native_headers], forbidden=[sysroot, target])
        if path.startswith(work_root + '/'):
            continue
        required.append(path)
        hashes.setdefault(path, sdk.digest(path))
    command = [*compile_args, *host_ldflags, *host_libs, *host_system, '-o', work + '/bin/llvm-config.real']
    sdk.command_file(Path(work) / 'compile.command', command)
    sdk.produce(command, Path(work) / 'compile.log')
    runtime = None
    if native_platform == 'linux-gnu':
        runtime = native_api.retain(work + '/bin/llvm-config.real', work, native_triple, compiler_runtime, forbidden=[target, sysroot])
        for f in runtime['files']:
            required.append(f['source'])
            hashes[f['source']] = f['sha256']
        for p, value in runtime['tools'].items():
            required.append(p)
            hashes[p] = value
    else:
        native_api.darwin(work + '/bin/llvm-config.real', native_triple)
    triple_query = [work + '/bin/llvm-config.real', '--host-target']
    if runtime:
        triple_query = [work + '/' + runtime['loader'], '--inhibit-cache', '--library-path', work + '/native/lib', *triple_query]
    reported = native_api.capture(*triple_query)
    require(target_api.for_triple(reported) == spec, 'upstream reported target disagrees with generated target metadata')
    required += list(sdk_inputs)
    hashes.update(sdk_inputs)
    receipt = dict(version=VERSION, source=source, target_build=target, native_build=native, native_sdk=native_sdk, native_platform=native_platform, native_triple=native_triple, native_header_roots=native_headers, native_system_libraries=host_system, native_linker_flags=host_ldflags, native_runtime=runtime, sysroot=sysroot, target_prefix=prefix, configured_target_triple=string(td, 'LLVM_HOST_TRIPLE'), target_triple=reported, target_triple_query=triple_query, target_assertions=tc['LLVM_ENABLE_ASSERTIONS'], staged_library_sha256=library_hash, library_proof=proof, compiler=cxx, compiler_version=sdk.capture(cxx, '--version'), original_ldflags=original_ldflags, mapped_ldflags=mapped_ldflags, command=command, host_api=1, sdk_source=sdk_root, host_python=sys.version, host_mechanism_inputs=sdk_inputs, sdk_source_provenance=sdk_provenance)
    sdk.write_json(Path(work) / 'receipt.json', receipt)
    shasum = native_api.executable('shasum')
    launcher = '#!/bin/sh\n# SPDX-License-Identifier: BSD-2-Clause\n# Integrity only; queries run the real upstream executable.\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)\ncd "$base"\n' + shlex.quote(shasum) + ' -a 256 -c inputs.sha256 > /dev/null || {\n    echo "llvm-config: input receipt changed; rebuild metadata tool" >&2\n    exit 1\n}\n' + native_api.launcher(runtime) + '\n'
    (Path(work) / 'bin/llvm-config').write_text(launcher)
    (Path(work) / 'bin/llvm-config').chmod(0o755)
    local = LOCAL + ['dependencies.log', 'compile.log']
    if runtime:
        local += [f['path'] for f in runtime['files']]
    if proof and proof['method'] == 'cmake-install-strip':
        local += ['strip.command', 'strip.log']
    required = list(dict.fromkeys(required))
    for p in required:
        require(sdk.digest(p) == hashes[p], 'input changed during compilation: ' + p + '; retain partial work')
    manifest = [hashes[p] + '  ' + p + '\n' for p in required]
    manifest += [sdk.digest(Path(work) / p) + '  ' + p + '\n' for p in local]
    (Path(work) / 'inputs.sha256').write_text(''.join(manifest))
    require(git_source(sdk_root, env=sdk.environment()) == sdk_provenance, 'SDK source changed during compilation')
    sdk.publish(work, destination)
    print(destination + '/bin/llvm-config')
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(build))
