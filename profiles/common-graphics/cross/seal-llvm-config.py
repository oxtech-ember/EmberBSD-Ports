#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Separate accepted build provenance from use.
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


def require(condition, message):
    if not condition:
        raise ValueError(message)


def output_argument(command):
    outputs = [i for i, arg in enumerate(command) if arg == '-o']
    require(len(outputs) == 1 and outputs[0] + 1 < len(command), 'unsupported recorded helper output argument')
    return command[outputs[0] + 1]


def digest(path):
    return sdk.digest(path) if Path(path).is_file() else None


def seal(args):
    from emberbsd_sdk.process import ContextLocks
    require(len(args) == 3, 'usage: seal-llvm-config.py --sdk-source SDK ACCEPTED_WORK ORIGINAL_MANIFEST_SHA256 NEW_WORK')
    old = sdk.existing_directory(args[0])
    expected = args[1]
    destination = sdk.new_destination(args[2], [old])
    with ContextLocks([old, destination], str(Path(destination).parent)):
        sdk.new_destination(destination, [old])
        return seal_locked(old, expected, destination)


def seal_locked(old, expected, destination):
    manifest_path = old + '/inputs.sha256'
    require(re.fullmatch(r'[0-9a-f]{64}', expected) and digest(manifest_path) == expected, 'original manifest hash mismatch')
    manifest = {}
    for line in Path(manifest_path).read_text().splitlines(keepends=True):
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)\n', line)
        require(match and not re.search(r'[\s\x00-\x1f\x7f]', match[2]) and '..' not in match[2].split('/'), 'malformed original manifest')
        require(match[2] not in manifest, 'duplicate original input')
        manifest[match[2]] = match[1]
    require(manifest.get('receipt.json') and digest(old + '/receipt.json') == manifest['receipt.json'], 'original receipt mismatch')
    r = sdk.read_json(old + '/receipt.json')
    native_platform = r.get('native_platform', 'darwin')
    require(native_platform in ('darwin', 'linux-gnu'), 'unsupported native platform')
    keys = ['source', 'target_build', 'native_build', 'sysroot', 'target_prefix', 'compiler']
    if native_platform == 'darwin':
        keys.append('native_sdk')
    for key in keys:
        require(sdk.safe_absolute(r[key]), 'unsupported receipt path ' + key)
    darwin_runtime = r.get('native_darwin_runtime') if native_platform == 'darwin' else None
    native_roots = r['native_header_roots'] if darwin_runtime or native_platform != 'darwin' else [r['native_sdk']]
    require(isinstance(native_roots, list) and native_roots and all(sdk.safe_absolute(p) and p != '/' for p in native_roots), 'unsupported native header search roots')
    runtime = r['native_runtime'] if native_platform == 'linux-gnu' else None
    require(native_platform != 'linux-gnu' or isinstance(runtime, dict), 'missing native Linux runtime receipt')
    source, target, native, prefix = [r[k] for k in ('source', 'target_build', 'native_build', 'target_prefix')]
    require(r.get('version') == '23.1.4' and prefix == r['sysroot'] + '/usr/pkg', 'requires an accepted installed LLVM 23.1.4 helper')
    if r.get('installed_headers_proof'):
        require(target_api.installed_headers(prefix) == r['installed_headers_proof'], 'installed LLVM header tree changed')
    spec = target_api.for_triple(r['target_triple'])
    proof = r['library_proof']
    require(proof['method'] in ('identical', 'cmake-install-strip') and proof['built_library'] == target + '/lib/libLLVM.so' and proof['staged_library'] == prefix + '/lib/libLLVM-23.so' and proof['staged_sha256'] == r['staged_library_sha256'] and proof['built_sha256' if proof['method'] == 'identical' else 'reproduced_sha256'] == proof['staged_sha256'], 'unsupported historical library proof')
    local = ['metadata/BuildVariables.inc', 'metadata/LibraryDependencies.inc', 'metadata/ExtensionDependencies.inc', 'llvm-config.cpp', 'llvm-config.d', 'dependencies.command', 'compile.command', 'receipt.json', 'bin/llvm-config.real', 'bin/llvm-config']
    # The explicit variants also allow migration qualification of authentic old receipts.
    # No old executable is invoked by this producer.
    if 'build-llvm-config.py' in manifest:
        local += ['build-llvm-config.py', 'llvm_target.py', 'llvm_native.py', 'llvm_sdk.py', 'dependencies.log', 'compile.log']
        if 'llvm_darwin_binding.py' in manifest:
            local.append('llvm_darwin_binding.py')
    else:
        local.append('build-llvm-config.rb')
        local += [p for p in ('llvm-target.rb', 'llvm-native.rb') if p in manifest]
    native_files = [f['path'] for f in runtime['files']] if runtime else []
    if runtime:
        require('llvm_native.py' in manifest or 'llvm-native.rb' in manifest, 'missing accepted native inspector')
        require(manifest.get('bin/llvm-config.real') and digest(old + '/bin/llvm-config.real') == manifest['bin/llvm-config.real'], 'accepted native executable mismatch')
        require(runtime['triple'] == r['native_triple'], 'native receipt triples differ')
        native_api.verify(old + '/bin/llvm-config.real', old, runtime)
        local += native_files
    if darwin_runtime:
        library_path = darwin_runtime['library']
        target_name = darwin_runtime['linker_target']
        require(re.fullmatch(r'libc\+\+[A-Za-z0-9_.-]*\.dylib', target_name) and library_path == 'native-darwin/lib/' + target_name, 'unsupported Darwin runtime path')
        require(darwin_runtime['library_sha256'] == manifest.get(library_path), 'Darwin runtime hash differs from manifest')
        local.append(library_path)
    if proof['method'] == 'cmake-install-strip':
        local += ['strip.command', 'strip.log']
    for p in local:
        require(manifest.get(p) and digest(old + '/' + p) == manifest[p], 'accepted local artifact mismatch: ' + p)
    metadata_names = ['include/llvm/Config/llvm-config.h', 'include/llvm/Config/config.h', 'include/llvm/Config/abi-breaking.h', 'tools/llvm-config/BuildVariables.inc', 'tools/llvm-config/LibraryDependencies.inc', 'tools/llvm-config/ExtensionDependencies.inc']
    classes = {p: 'accepted-local-artifact' for p in local}
    classes.update({target + '/' + p: 'target-report-metadata' for p in metadata_names})
    classes.update({prefix + '/include/llvm/Config/' + p: 'installed-target-input' for p in ('llvm-config.h', 'abi-breaking.h')})
    classes[proof['staged_library']] = 'installed-target-input'
    historical = [target + '/CMakeCache.txt', native + '/CMakeCache.txt', proof['built_library'], r['compiler'], source + '/tools/llvm-config/llvm-config.cpp', native + '/bin/llvm-config']
    historical += [native + '/include/llvm/Config/' + p for p in ('llvm-config.h', 'config.h', 'abi-breaking.h')]
    historical += [native + '/lib/lib' + p + '.a' for p in ('LLVMTargetParser', 'LLVMSupport', 'LLVMDemangle')]
    historical += [p for p in r.get('native_system_libraries', []) if p.startswith('/')]
    for p, value in r.get('host_mechanism_inputs', {}).items():
        require(sdk.safe_absolute(p) and manifest.get(p) == value, 'host mechanism hash differs from original manifest')
        historical.append(p)
    if runtime:
        sources = {f['source']: f['sha256'] for f in runtime['files']}
        sources.update(runtime['tools'])
        for p, value in sources.items():
            require(sdk.safe_absolute(p) and manifest.get(p) == value, 'native runtime/tool source hash differs from original manifest')
            historical.append(p)
    if r.get('installed_headers_proof'):
        historical.append(target + '/install_manifest.txt')
    if darwin_runtime:
        historical += [darwin_runtime['binding'], *darwin_runtime['sources']]
    if proof['method'] == 'cmake-install-strip':
        require(sdk.safe_absolute(proof['strip']) and proof['install_script'] == target + '/tools/llvm-shlib/cmake_install.cmake', 'unsupported strip proof paths')
        historical += [proof['strip'], proof['install_script']]
    depfile = Path(old + '/llvm-config.d').read_text().replace('\\\n', ' ')
    require(depfile.startswith('llvm-config:'), 'unsupported dependency file')
    compile_sources = [a for a in r['command'] if a.endswith('/llvm-config.cpp')]
    require(len(compile_sources) == 1, 'unsupported recorded helper compile command')
    compile_work = str(Path(compile_sources[0]).parent)
    require(sdk.safe_absolute(compile_work) and '-I' + compile_work + '/metadata' in r['command'] and output_argument(r['command']) == compile_work + '/bin/llvm-config.real', 'unsupported recorded helper work path')
    for p in shlex.split(re.sub(r'^llvm-config:\s*', '', depfile)):
        if p.startswith(compile_work + '/'):
            require(sdk.safe_absolute(p), 'unsafe local compile dependency: ' + p)
            require(p.removeprefix(compile_work + '/') in local, 'unknown local compile dependency: ' + p)
            continue
        canonical = native_api.validate_header(p, [source + '/include', native + '/include', *native_roots], forbidden=[target, prefix, r['sysroot']])
        historical.append(canonical)
    original_vars = target + '/tools/llvm-config/BuildVariables.inc'
    require(manifest.get(original_vars) and digest(original_vars) == manifest[original_vars], 'target report metadata mismatch')
    match = re.search(r'^#define LLVM_SRC_ROOT (".*")$', Path(original_vars).read_text(), re.M)
    require(match, 'missing original target source root')
    original_source = json_string(match[1])
    require(sdk.safe_absolute(original_source), 'unsupported original target source path')
    historical.append(original_source + '/tools/llvm-config/llvm-config.cpp')
    for p in historical:
        classes.setdefault(p, 'historical-build-input')
    require(not set(manifest) - set(classes), 'unclassified original inputs: ' + ', '.join(set(manifest) - set(classes)))
    require(not set(classes) - set(manifest), 'missing required original inputs: ' + ', '.join(set(classes) - set(manifest)))
    require(manifest[proof['built_library']] == proof['built_sha256'] and manifest[proof['staged_library']] == proof['staged_sha256'], 'library proof differs from original manifest')
    rows = []
    for p, value in manifest.items():
        actual = digest(p if p.startswith('/') else old + '/' + p)
        state = 'missing' if actual is None else ('match' if actual == value else 'changed')
        require(classes[p] == 'historical-build-input' or state == 'match', 'required ' + classes[p] + ' mismatch: ' + p)
        rows.append(dict(path=p, classification=classes[p], expected_sha256=value, observed_sha256=actual, state=state))
    library = proof['staged_library']
    require(str(Path(library).resolve(strict=True)).startswith(prefix + '/lib/'), 'installed shared LLVM resolves outside the target prefix')
    target_api.validate_elf(library, spec)
    allowed = []
    if darwin_runtime:
        canonical = Path(darwin_runtime['canonical_lib'])
        require(canonical.is_absolute() and canonical.name == 'lib', 'invalid selected Darwin library prefix')
        allowed = darwin_runtime['allowed']
        flags = [flag for flag in r['native_system_libraries'] if flag != '-lm']
        require(len(allowed) == len(darwin_runtime['sources']) == 1 + len(flags) and allowed[0] == str(canonical / 'libc++' / target_name), 'invalid selected Darwin runtime closure')
        for flag, name, source_path in zip(flags, allowed[1:], darwin_runtime['sources'][1:]):
            require(re.fullmatch(r'-l[A-Za-z0-9_+.-]+', flag) and Path(name).parent == canonical and re.fullmatch(re.escape('lib' + flag[2:]) + r'(?:\.[0-9]+)*\.dylib', Path(name).name), 'invalid selected Darwin dependency')
            require(digest(name) == manifest.get(source_path), 'installed Darwin dependency differs from selected input')
    linked = native_api.verify(old + '/bin/llvm-config.real', old, runtime) if runtime else native_api.darwin(old + '/bin/llvm-config.real', r['native_triple'], allowed=allowed)
    work = sdk.stage_for(destination)
    print('Retained partial work on failure: ' + work, file=sys.stderr, flush=True)
    (Path(work) / 'provenance').mkdir()
    shutil.copyfile(manifest_path, Path(work) / 'provenance/inputs.sha256')
    for p in local:
        if p in native_files:
            continue
        destination_name = 'provenance/original-launcher' if p == 'bin/llvm-config' else p
        output = Path(work) / destination_name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old + '/' + p, output)
        require(digest(output) == manifest[p], 'copied local artifact changed: ' + p)
    (Path(work) / 'bin/llvm-config.real').chmod(0o755)
    if runtime:
        native_api.copy(old + '/bin/llvm-config.real', old, work, runtime, copied_binary=work + '/bin/llvm-config.real')
    shutil.copyfile(old + '/receipt.json', Path(work) / 'provenance/receipt.json')
    for p in metadata_names:
        output = Path(work) / 'provenance/target' / p
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target + '/' + p, output)
        require(digest(output) == manifest[target + '/' + p], 'target metadata changed while copying: ' + p)
    shutil.copyfile(__file__, Path(work) / 'seal-llvm-config.py')
    (Path(work) / 'provenance/native-loader.txt').write_text(linked)
    sdk.write_json(Path(work) / 'seal.json', dict(format='ember-llvm-config-seal-v1', original_manifest_sha256=expected,
        accepted_executable_sha256=manifest['bin/llvm-config.real'], original_work=old,
        historical_proof='Original strip/build proof is retained as accepted provenance; it is not reproduced by sealing.', observed_inputs=rows))
    launch = native_api.launcher(runtime)
    if darwin_runtime:
        launch = ('exec /usr/bin/env -i PATH=\"$PATH\" HOME=\"${HOME:-/}\" TMPDIR=\"${TMPDIR:-/tmp}\" ' +
                  shlex.join([darwin_runtime['python'], '-B', darwin_runtime['sdk_source'] + '/scripts/run-darwin-with-runtime.py']) +
                  ' --runtime-view \"$base/native-darwin/lib\" -- \"$base/bin/llvm-config.real\" \"$@\"')
    launcher = '#!/bin/sh\n# SPDX-License-Identifier: BSD-2-Clause\n# Run the selected native query tool.\nset -eu\nbase=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")/.." && pwd -P)\ncd "$base"\n' + launch + '\n'
    (Path(work) / 'bin/llvm-config').write_text(launcher)
    (Path(work) / 'bin/llvm-config').chmod(0o755)
    files = sorted(p for p in Path(work).rglob('*') if p.is_file())
    installed = [row for row in rows if row['classification'] == 'installed-target-input']
    for row in installed:
        require(digest(row['path']) == row['expected_sha256'], 'installed input changed while sealing: ' + row['path'])
    require(digest(manifest_path) == expected, 'original manifest changed while sealing')
    lines = [digest(p) + '  ' + str(p.relative_to(work)) + '\n' for p in files]
    lines += [row['expected_sha256'] + '  ' + row['path'] + '\n' for row in installed]
    (Path(work) / 'inputs.sha256').write_text(''.join(lines))
    sdk.publish(work, destination)
    print(destination + '/bin/llvm-config')
    print('Same accepted executable; ' + str(sum(row['state'] != 'match' for row in rows)) + ' historical input changes recorded, not revalidated.')
    return 0


def json_string(value):
    import json
    result = json.loads(value)
    require(isinstance(result, str), 'unsupported C string')
    return result


if __name__ == '__main__':
    sys.exit(sdk.main(seal))
