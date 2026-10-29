#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise real metadata and refusal paths.
import importlib.util
from pathlib import Path
import re
import shlex
import shutil
import sys
sys.dont_write_bytecode = True
import llvm_sdk as sdk
import llvm_target as target_api


def target_cxxflags_match(output, expected, native_build):
    try:
        flags = shlex.split(output)
    except ValueError:
        return False
    return flags == expected and '-fno-rtti' not in flags and native_build not in output


def target_cxxflags_fixture_contract():
    include = '-I/fixture/target/usr/pkg/include'
    native_build = '/fixture/native-build'
    without_abi = [include, '-std=c++17']
    with_abi = [*without_abi, '-D_GLIBCXX_USE_CXX11_ABI=1']
    cases = (
        ('target metadata without an ABI macro', without_abi, without_abi, True),
        ('target metadata with its declared ABI macro', with_abi, with_abi, True),
        ('missing declared ABI macro', without_abi, with_abi, False),
        ('changed declared ABI macro', [*without_abi, '-D_GLIBCXX_USE_CXX11_ABI=0'], with_abi, False),
        ('extra conflicting ABI macro', [*with_abi, '-D_GLIBCXX_USE_CXX11_ABI=0'], with_abi, False),
    )
    return all(target_cxxflags_match(' '.join(actual), expected, native_build) == accepted
               for _, actual, expected, accepted in cases)


def test(args):
    if len(args) != 2:
        raise ValueError('usage: test-llvm-config.py --sdk-source SDK COMPLETED_WORK NEW_TEST_WORK')
    work = Path(sdk.existing_directory(args[0]))
    tmp = Path(sdk.new_destination(args[1], [str(work)]))
    tmp.mkdir()
    r = sdk.read_json(work / 'receipt.json')
    spec = target_api.for_triple(r['target_triple'])
    tool = str(work / 'bin/llvm-config')
    builder = str(Path(__file__).with_name('build-llvm-config.py'))
    builder_spec = importlib.util.spec_from_file_location('llvm_config_builder', builder)
    if builder_spec is None or builder_spec.loader is None:
        raise ValueError('Cannot load the llvm-config builder parser')
    builder_module = importlib.util.module_from_spec(builder_spec)
    builder_spec.loader.exec_module(builder_module)
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError('FAIL: ' + name)
        checks.append(name)
        print('PASS: ' + name, flush=True)

    options = ['--relocated-installed-prefix'] if r.get('relocated_installed_prefix') else []
    if r.get('native_darwin_runtime'):
        selected = r['native_darwin_runtime']
        options += ['--native-cxx-binding', selected['binding'], '--runtime-view', selected['view']]

    def refusal(name, inputs, output, message):
        command = [sys.executable, builder, '--sdk-source', sdk.sdk_source.load(), *options, *inputs, str(output)]
        out, err, status = sdk.query(*command, env={'NATIVE_CXX': r['compiler']})
        sdk.write_json(tmp / (output.name + '.json'), dict(command=command, stdout=out, stderr=err, exit=status))
        check(name, status != 0 and message in err and (output == work or not output.exists()))

    check('C++ ABI fixtures follow declared target metadata exactly', target_cxxflags_fixture_contract())
    out, _, status = sdk.query(tool, '--version', '--host-target', '--has-rtti', '--assertion-mode')
    check('actual upstream tool reports target version/triple/RTTI/assertions', status == 0 and out == f"23.1.4\n{r['target_triple']}\nYES\n{r.get('target_assertions', 'OFF')}\n")
    out, _, status = sdk.query(tool, '--components')
    required = ['aarch64', 'amdgpu', 'riscv', 'x86', 'xtensa', 'orcjit', 'jitlink', 'native'] if spec['processor'] == 'aarch64' else ['x86', 'orcjit', 'jitlink', 'native']
    check('target component graph includes the selected backend and ORC', status == 0 and set(required) <= set(out.split()))
    target_variables = builder_module.definitions(
        str(Path(r['target_build']) / 'tools/llvm-config/BuildVariables.inc'))
    expected_cxxflags = ['-I' + r['target_prefix'] + '/include',
                         *shlex.split(builder_module.string(target_variables, 'LLVM_CXXFLAGS'))]
    out, _, status = sdk.query(tool, '--cxxflags')
    check('compiler flags match target BuildVariables.inc and preserve the target C++ ABI',
          status == 0 and target_cxxflags_match(out, expected_cxxflags, r['native_build']))
    out, _, status = sdk.query(tool, '--ldflags')
    check('search paths use target sysroot while runtime paths stay target paths', status == 0 and '-L' + r['sysroot'] + '/usr/lib' in out and '-Wl,-R/usr/lib' in out and not re.search(r'(?:^| )-L/usr/', out) and 'darwin' not in out)
    _, err, status = sdk.query(tool, '--link-static', '--libs', 'ember_nonexistent_component')
    check('upstream rejects an unknown component', status != 0 and 'unknown component' in err)
    fixture = tmp / 'changed-historical-manifest'
    shutil.copytree(work, fixture)
    with (fixture / 'inputs.sha256').open('a') as stream:
        stream.write('0' * 64 + '  /unrelated/sdk/module.py\n')
    out, _, status = sdk.query(str(fixture / 'bin/llvm-config'), '--version')
    check('unrelated historical SDK input does not block queries', status == 0 and out.strip() == '23.1.4')
    inputs = [r[k] for k in ('source', 'target_build', 'native_build', 'sysroot', 'target_prefix')]
    refusal('rejects native metadata as target input', [r['source'], r['native_build'], r['native_build'], r['sysroot'], r['target_prefix']], tmp / 'wrong-target', 'target must be configured for NetBSD/aarch64')
    refusal('rejects a native prefix substituted for the target payload', [*inputs[:4], r['native_build']], tmp / 'wrong-prefix', 'relocated mode requires an installed /usr/pkg prefix' if r.get('relocated_installed_prefix') else 'staged target header missing or mismatched')
    refusal('rejects an existing destination before edits', inputs, work, 'NEW_WORK must be absolute and absent')
    if r['target_prefix'] != r['target_build']:
        proof = r['library_proof']
        actual = sdk.digest(proof['staged_library'])
        check('staged shared library has a reproducible build-output identity', actual == proof['staged_sha256'] == proof['built_sha256' if proof['method'] == 'identical' else 'reproduced_sha256'])
        changed_root = tmp / 'changed-sysroot'
        changed = changed_root / 'usr/pkg'
        (changed / 'include').mkdir(parents=True)
        (changed / 'lib').mkdir()
        for name in ('llvm', 'llvm-c'):
            shutil.copytree(Path(r['target_prefix']) / 'include' / name, changed / 'include' / name)
        shutil.copyfile(proof['staged_library'], changed / 'lib/libLLVM-23.so')
        with (changed / 'lib/libLLVM-23.so').open('ab') as stream:
            stream.write(b'changed staged payload')
        refusal('rejects a changed staged shared library after exact strip reproduction', [*inputs[:3], str(changed_root), str(changed)], tmp / 'wrong-library', 'differs from the reproduced CMake install-strip output')
    changed_source = tmp / 'source'
    (changed_source / 'tools/llvm-config').mkdir(parents=True)
    (changed_source / 'tools/llvm-config/llvm-config.cpp').write_text(Path(r['source'] + '/tools/llvm-config/llvm-config.cpp').read_text() + '\n// changed upstream input\n')
    refusal('rejects changed upstream llvm-config source', [str(changed_source), *inputs[1:]], tmp / 'wrong-source', 'differs from LLVM 23.1.4')
    changed = tmp / 'leaked-target'
    names = ['CMakeCache.txt', 'include/llvm/Config/llvm-config.h', 'include/llvm/Config/config.h', 'include/llvm/Config/abi-breaking.h', 'tools/llvm-config/BuildVariables.inc', 'tools/llvm-config/LibraryDependencies.inc', 'tools/llvm-config/ExtensionDependencies.inc']
    for name in names:
        output = changed / name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(r['target_build'] + '/' + name, output)
    variables = changed / 'tools/llvm-config/BuildVariables.inc'
    import json
    contents = re.sub(r'^#define LLVM_OBJ_ROOT .*$', '#define LLVM_OBJ_ROOT ' + json.dumps(str(changed)), variables.read_text(), flags=re.M)
    contents = re.sub(r'^#define LLVM_LDFLAGS .*$', '#define LLVM_LDFLAGS ' + json.dumps('-L' + r['sysroot'] + '/usr/pkg/lib'), contents, flags=re.M)
    variables.write_text(contents)
    if r.get('relocated_installed_prefix'):
        values = builder_module.definitions(str(variables))
        try:
            builder_module.target_flags(values, r['source'], str(changed), r['native_build'], r['sysroot'], r['sysroot'])
        except ValueError as exc:
            check('rejects private sysroot leaked into target metadata', 'LLVM_LDFLAGS leaks CMAKE_SYSROOT' in str(exc))
        else:
            check('rejects private sysroot leaked into target metadata', False)
    else:
        refusal('rejects private sysroot leaked into target metadata', [r['source'], str(changed), *inputs[2:4], str(changed)], tmp / 'wrong-metadata', 'LLVM_LDFLAGS leaks CMAKE_SYSROOT')
    if r.get('library_proof', {}).get('method') == 'cmake-install-strip':
        contents = re.sub(r'^#define LLVM_LDFLAGS .*$', '#define LLVM_LDFLAGS ' + json.dumps(r['original_ldflags']), contents, flags=re.M)
        variables.write_text(contents)
        path = changed / 'CMakeCache.txt'
        path.write_text(re.sub(r'^CMAKE_STRIP:FILEPATH=.*$', 'CMAKE_STRIP:FILEPATH=/usr/bin/true', path.read_text(), flags=re.M))
        (changed / 'tools/llvm-shlib').mkdir(parents=True)
        shutil.copyfile(r['library_proof']['install_script'], changed / 'tools/llvm-shlib/cmake_install.cmake')
        (changed / 'lib').mkdir()
        (changed / 'lib/libLLVM.so').symlink_to(Path(r['library_proof']['built_library']).resolve(strict=True))
        if r.get('relocated_installed_prefix'):
            shutil.copyfile(Path(r['target_build']) / 'install_manifest.txt', changed / 'install_manifest.txt')
            shutil.copytree(Path(r['target_build']) / 'include/llvm', changed / 'include/llvm', dirs_exist_ok=True)
            refusal('rejects strip metadata inconsistent with actual install script', [r['source'], str(changed), r['native_build'], str(changed_root), str(changed_root / 'usr/pkg')], tmp / 'wrong-strip', 'unsupported shared LLVM install/strip transformation')
        else:
            refusal('rejects strip metadata inconsistent with actual install script', [r['source'], str(changed), *inputs[2:]], tmp / 'wrong-strip', 'unsupported shared LLVM install/strip transformation')
    out, err, status = sdk.query(tool, '--link-shared', '--shared-mode', 'core', 'executionengine', 'orcjit', 'native')
    check('upstream accepts the available shared LLVM library' if Path(r['target_prefix'] + '/lib/libLLVM-23.so').exists() else 'upstream refuses a missing shared LLVM library', (status == 0 and out == 'shared\n') if Path(r['target_prefix'] + '/lib/libLLVM-23.so').exists() else (status != 0 and 'libLLVM-23.so is missing' in err))
    sdk.write_json(tmp / 'result.json', dict(checks=checks, scope='Real native upstream metadata queries and deliberate input refusals; no target execution'))
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(test))
