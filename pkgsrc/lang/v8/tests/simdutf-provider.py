#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check V8 receives simdutf include paths from the selected GN provider."""

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

PATCH = 'patch-v8_BUILD.gn-simdutf-provider'
V8_BUILD = 'BUILD.gn'
V8_GROUP = 'group("v8_simdutf") {'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--v8-source', type=Path, required=True,
                    help='prepared common V8 source before this recipe patch')
parser.add_argument('--chromium-source', type=Path, required=True,
                    help='prepared Chromium source with gn-shared-simdutf.patch applied')
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--gn', type=Path, required=True)
parser.add_argument('--clangxx', type=Path, required=True)
parser.add_argument('--ld64', type=Path, required=True)
parser.add_argument('--patch', type=Path, required=True)
parser.add_argument('--macos-sdk', type=Path, required=True)
args = parser.parse_args()

repo = Path(__file__).resolve().parents[1]
host = args.host_prefix.resolve(strict=True)
v8_source = args.v8_source.resolve(strict=True)
chromium_source = args.chromium_source.resolve(strict=True)
gn = args.gn.resolve(strict=True)
clangxx = args.clangxx.resolve(strict=True)
ld64 = args.ld64.absolute()
ld64_real = ld64.resolve(strict=True)
patch_tool = args.patch.resolve(strict=True)
sdk = args.macos_sdk.resolve(strict=True)
patch = repo / 'patches' / PATCH
series = repo / 'distinfo'
for tool in (gn, clangxx, ld64_real, patch_tool):
    if not tool.is_file() or not tool.is_relative_to(host):
        parser.error('GN, Clang, ld64.lld and patch must come from the selected host prefix')
if not v8_source.is_dir() or not chromium_source.is_dir() or not sdk.is_dir() or not patch.is_file():
    parser.error('V8/Chromium sources, patch and macOS SDK must exist')
if not any(line.startswith('SHA1 (' + PATCH + ') = ') for line in
           series.read_text(encoding='utf-8').splitlines()):
    parser.error('V8 provider patch is not declared in distinfo')
simdutf_makefile = repo.parents[1] / 'devel/simdutf/Makefile'
simdutf_pc = host / 'lib/pkgconfig/simdutf.pc'
if not simdutf_makefile.is_file() or not simdutf_pc.is_file():
    parser.error('common simdutf recipe and selected pkg-config metadata must exist')
recipe_version = re.search(r'^DISTNAME=\s*simdutf-([0-9.]+)$',
                           simdutf_makefile.read_text(encoding='utf-8'), re.M)
pc_text = simdutf_pc.read_text(encoding='utf-8')
pc_prefix = re.search(r'^prefix=(.+)$', pc_text, re.M)
pc_version = re.search(r'^Version:\s*(\S+)$', pc_text, re.M)
if (not recipe_version or not pc_prefix or not pc_version or
        pc_version.group(1) != recipe_version.group(1) or
        Path(pc_prefix.group(1)).resolve() != host):
    parser.error('selected simdutf pkg-config metadata does not match the common recipe/prefix')

def block(text, marker):
    if text.count(marker) != 1:
        raise SystemExit('missing or ambiguous production GN block: ' + marker)
    start = text.index(marker)
    opening = text.index('{', start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise SystemExit('unterminated production GN block: ' + marker)

source_v8_build = v8_source / V8_BUILD
provider_build = chromium_source / 'third_party/simdutf/BUILD.gn'
provider_gni = chromium_source / 'third_party/simdutf/simdutf.gni'
bundled_header = chromium_source / 'third_party/simdutf/simdutf.h'
for path in (source_v8_build, provider_build, provider_gni, bundled_header):
    if not path.is_file() or path.is_symlink():
        parser.error('missing regular prepared GN input: ' + str(path))
original_v8 = source_v8_build.read_text(encoding='utf-8')
original_group = block(original_v8, V8_GROUP)
provider_text = provider_build.read_text(encoding='utf-8')
if 'use_system_simdutf' not in provider_text:
    parser.error('Chromium source does not contain the shared simdutf provider integration')

sdk_version = json.loads((sdk / 'SDKSettings.json').read_text(encoding='utf-8')).get('Version')
if not isinstance(sdk_version, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', sdk_version):
    parser.error('selected macOS SDK has no numeric SDK version')
host_arch = {'aarch64': 'arm64', 'amd64': 'x86_64'}.get(
    platform.machine().lower(), platform.machine().lower())
if host_arch not in ('arm64', 'x86_64'):
    parser.error('simdutf regression requires an arm64 or x86_64 Darwin host')
resource = Path(subprocess.run([str(clangxx), '-print-resource-dir'],
                               capture_output=True, text=True, check=True).stdout.strip())
resource = resource.resolve(strict=True)
if not resource.is_relative_to(host):
    parser.error('selected Clang resource directory is outside the selected host prefix')

def run(command, *, cwd, env):
    return subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                          capture_output=True, text=True)

def includes(root, out):
    env = {'PATH': str(host / 'bin'),
           'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())}
    result = run([gn, 'desc', out, '//v8:consumer', 'include_dirs', '--format=json'],
                 cwd=root, env=env)
    if result.returncode:
        raise SystemExit('gn desc failed:\n' + result.stdout + result.stderr)
    values = json.loads(result.stdout)
    target = values.get('//v8:consumer') if isinstance(values, dict) else None
    values = target.get('include_dirs') if isinstance(target, dict) else None
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise SystemExit('gn desc returned invalid include_dirs: ' + result.stdout)
    result = []
    for value in values:
        path = (root / value[2:]) if value.startswith('//') else Path(value)
        if not path.is_absolute():
            path = root / path
        result.append(path.resolve())
    return result

def create_fixture(root, v8_group, v8_config):
    root.mkdir(parents=True, exist_ok=True)
    (root / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n', encoding='utf-8')
    (root / 'BUILDCONFIG.gn').write_text('''
declare_args() {
  is_win = false
  is_debug = true
}
set_defaults("source_set") {
  configs = [ "//build/config/compiler:chromium_code" ]
}
set_default_toolchain("//toolchain:default")
''', encoding='utf-8')
    (root / 'BUILD.gn').write_text('group("all") { deps = [ "//v8:consumer" ] }\n', encoding='utf-8')
    (root / 'toolchain/BUILD.gn').parent.mkdir(parents=True)
    (root / 'toolchain/BUILD.gn').write_text('toolchain("default") {}\n', encoding='utf-8')
    (root / 'build/config/avx512.gni').parent.mkdir(parents=True)
    (root / 'build/config/avx512.gni').write_text(
        'declare_args() { allow_avx512 = false }\n', encoding='utf-8')
    (root / 'build/config/compiler').mkdir(parents=True)
    (root / 'build/config/compiler/BUILD.gn').write_text(
        'config("chromium_code") {}\nconfig("no_chromium_code") {}\n', encoding='utf-8')
    pkgconfig = root / 'build/config/linux/pkg_config.gni'
    pkgconfig.parent.mkdir(parents=True)
    pkgconfig.write_text('''
template("pkg_config") {
  config(target_name) {
    include_dirs = [ "//external/include" ]
    libs = invoker.packages
  }
}
''', encoding='utf-8')
    provider = root / 'third_party/simdutf'
    provider.mkdir(parents=True)
    shutil.copyfile(provider_build, provider / 'BUILD.gn')
    shutil.copyfile(provider_gni, provider / 'simdutf.gni')
    shutil.copyfile(bundled_header, provider / 'simdutf.h')
    (provider / 'simdutf.cpp').write_text('', encoding='utf-8')
    external_include = root / 'external/include'
    external_include.parent.mkdir(parents=True)
    external_include.symlink_to(host / 'include', target_is_directory=True)
    v8 = root / 'v8'
    v8.mkdir()
    (v8 / 'BUILD.gn').write_text(v8_group + '\n' + v8_config + '''
source_set("consumer") {
  sources = [ "consumer.cc" ]
  deps = [ ":v8_simdutf" ]
}
''', encoding='utf-8')
    (v8 / 'consumer.cc').write_text('#include <simdutf.h>\n', encoding='utf-8')

def generate(root, mode, use_system):
    out = root / 'out' / mode
    out.mkdir(parents=True)
    (out / 'args.gn').write_text(
        'use_system_simdutf = ' + ('true' if use_system else 'false') + '\n',
        encoding='utf-8')
    env = {'PATH': str(host / 'bin'),
           'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())}
    generated = run([gn, 'gen', out, '--root=' + str(root)], cwd=root, env=env)
    if generated.returncode:
        raise SystemExit('gn gen ' + mode + ' failed:\n' + generated.stdout + generated.stderr)
    return includes(root, out)

def first_header(dirs):
    for directory in dirs:
        if (directory / 'simdutf.h').is_file():
            return directory
    raise SystemExit('GN emitted no directory containing simdutf.h')

def compile_consumer(root, dirs, *, expect_success):
    probe = root / 'simdutf-base64.cc'
    probe.write_text(r'''#include <simdutf.h>
int main() {
  if (simdutf::base64_length_from_binary(3, simdutf::base64_url) != 4) return 1;
  char output[8] = {};
  const auto decoded = simdutf::base64_to_binary("!!!!", 4, output);
  if (decoded.error == simdutf::SUCCESS) return 2;
  return 0;
}
''', encoding='utf-8')
    command = [str(clangxx), '-std=c++20', '-target', host_arch + '-apple-macosx14.0',
               '-arch', host_arch, '-isysroot', str(sdk), '-resource-dir', str(resource),
               '-nostdinc++', '-isystem', str(host / 'include/libc++/v1'),
               '-nostdlib++', '-fuse-ld=' + str(ld64), '-mmacosx-version-min=14.0',
               '-Wl,-platform_version,macos,14.0,' + sdk_version]
    for directory in dirs:
        command.extend(['-I', str(directory)])
    library = host / 'lib'
    binary = root / 'simdutf-base64'
    cxx_runtime = host / 'lib/libc++/libc++_ember1.1.dylib'
    if not cxx_runtime.is_file():
        raise SystemExit('selected native libc++ runtime is missing: ' + str(cxx_runtime))
    command.extend([str(probe), '-L' + str(library), '-lsimdutf', str(cxx_runtime),
                    '-Wl,-rpath,' + str(library), '-Wl,-rpath,' + str(cxx_runtime.parent),
                    '-o', str(binary)])
    build = run(command, cwd=root, env={'PATH': str(host / 'bin'),
                                        'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())})
    if expect_success:
        if build.returncode:
            raise SystemExit('provider-selected base64 compile/link failed:\n' +
                             build.stdout + build.stderr)
        execution = run([binary], cwd=root, env={'PATH': str(host / 'bin'),
                                                  'DYLD_LIBRARY_PATH': str(library) + ':' + str(cxx_runtime.parent)})
        if execution.returncode:
            raise SystemExit('base64 consumer returned ' + str(execution.returncode) +
                             ':\n' + execution.stdout + execution.stderr)
    elif build.returncode == 0 or 'base64_length_from_binary' not in build.stderr:
        raise SystemExit('baseline did not reproduce the bundled-header/common-library ABI mismatch:\n' +
                         build.stdout + build.stderr)

with tempfile.TemporaryDirectory(prefix='v8-simdutf-provider-') as temporary:
    root = Path(temporary)
    patch_tree = root / 'patch-check'
    (patch_tree / 'v8').mkdir(parents=True)
    shutil.copyfile(source_v8_build, patch_tree / 'v8/BUILD.gn')
    env = {'PATH': str(host / 'bin'),
           'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())}
    check = run([patch_tool, '--dry-run', '-p0', '-F0', '-i', patch],
                cwd=patch_tree / 'v8', env=env)
    if check.returncode:
        raise SystemExit('exact V8 recipe patch does not apply:\n' + check.stdout + check.stderr)
    applied = run([patch_tool, '-p0', '-F0', '-i', patch],
                  cwd=patch_tree / 'v8', env=env)
    if applied.returncode:
        raise SystemExit('exact V8 recipe patch failed:\n' + applied.stdout + applied.stderr)
    patched_text = (patch_tree / 'v8/BUILD.gn').read_text(encoding='utf-8')
    patched_group = block(patched_text, V8_GROUP)
    if 'simdutf_include_config' in patched_text:
        raise SystemExit('V8 retains its redundant simdutf include config')

    baseline = root / 'baseline'
    create_fixture(baseline, original_group, block(original_v8, 'config("simdutf_include_config") {'))
    baseline_dirs = generate(baseline, 'system', True)
    if first_header(baseline_dirs) != (baseline / 'third_party/simdutf').resolve():
        raise SystemExit('baseline did not prefer V8 bundled header over shared provider')
    compile_consumer(baseline, baseline_dirs, expect_success=False)

    system = root / 'system'
    create_fixture(system, patched_group, '')
    system_dirs = generate(system, 'system', True)
    if first_header(system_dirs) != (host / 'include').resolve():
        raise SystemExit('shared GN provider did not select the common simdutf header: ' +
                         repr(system_dirs))
    compile_consumer(system, system_dirs, expect_success=True)

    bundled = root / 'bundled'
    create_fixture(bundled, patched_group, '')
    bundled_dirs = generate(bundled, 'bundled', False)
    if first_header(bundled_dirs) != (bundled / 'third_party/simdutf').resolve():
        raise SystemExit('standalone GN provider did not select its bundled simdutf header')

print('PASS: GN transitive config selects external and bundled simdutf headers correctly')
print('PASS: V8 base64 size, invalid-input, common-library link and runtime regression')
