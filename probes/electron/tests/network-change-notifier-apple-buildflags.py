#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Apply the exact Ports patch and preprocess its Apple deployment matrix."""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

PATCH_NAME = 'network-change-notifier-apple-macos14.4.patch'
INPUTS = (
    'net/base/network_change_notifier_apple_buildflags.h',
    'net/base/network_change_notifier_apple.mm',
    'net/base/network_change_notifier_apple_unittest.cc',
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path,
                    help='prepared Chromium src immediately before this patch')
parser.add_argument('--git', required=True, type=Path)
parser.add_argument('--clang', required=True, type=Path,
                    help='selected native Clang preprocessor')
parser.add_argument('--clangxx', required=True, type=Path,
                    help='selected native Clang++ compiler')
parser.add_argument('--host-prefix', required=True, type=Path)
parser.add_argument('--target', required=True,
                    help='native macOS target triplet')
parser.add_argument('--sysroot', required=True, type=Path)
parser.add_argument('--deployment-target', required=True,
                    help='macOS deployment version, such as 15.0')
parser.add_argument('--resource-dir', required=True, type=Path)
parser.add_argument('--ld-path', required=True, type=Path,
                    help='selected prefix ld64.lld')
args = parser.parse_args()
source = args.source.resolve(strict=True)
git = args.git.resolve(strict=True)
clang = args.clang.resolve(strict=True)
clangxx = args.clangxx.resolve(strict=True)
host_prefix = args.host_prefix.resolve(strict=True)
sysroot = args.sysroot.resolve(strict=True)
resource_dir = args.resource_dir.resolve(strict=True)
ld_path = args.ld_path.resolve(strict=True)
patch = Path(__file__).resolve().parents[1] / 'patches' / PATCH_NAME
selected_tools = (clang, clangxx, resource_dir, ld_path)
if (not source.is_dir() or not git.is_file() or not patch.is_file() or
        not sysroot.is_dir() or not resource_dir.is_dir() or
        any(not tool.is_file() and not tool.is_dir() for tool in selected_tools) or
        any(not tool.is_relative_to(host_prefix) for tool in (clang, clangxx, resource_dir, ld_path))):
    parser.error('source, selected prefix tools/resources, SDK, Git, and patch must exist')

cases = (
    ('macOS 14.3', 1, 0, 0, {'__MAC_OS_X_VERSION_MIN_REQUIRED': 140300}, 1),
    ('macOS 14.4', 1, 0, 0, {'__MAC_OS_X_VERSION_MIN_REQUIRED': 140400}, 0),
    ('macOS 15.0', 1, 0, 0, {'__MAC_OS_X_VERSION_MIN_REQUIRED': 150000}, 0),
    ('iOS 17.3', 0, 1, 0, {'__IPHONE_17_4': 170400,
                            '__IPHONE_OS_VERSION_MIN_REQUIRED': 170300}, 1),
    ('iOS 17.4', 0, 1, 0, {'__IPHONE_17_4': 170400,
                            '__IPHONE_OS_VERSION_MIN_REQUIRED': 170400}, 0),
    ('tvOS 17.3', 0, 1, 1, {'__IPHONE_17_4': 170400,
                             '__IPHONE_OS_VERSION_MIN_REQUIRED': 170300}, 1),
    ('tvOS 17.4', 0, 1, 1, {'__IPHONE_17_4': 170400,
                             '__IPHONE_OS_VERSION_MIN_REQUIRED': 170400}, 0),
)

with tempfile.TemporaryDirectory(prefix='network-change-apple-') as temporary:
    root = Path(temporary)
    for relative in INPUTS:
        original = source / relative
        if not original.is_file() or original.is_symlink():
            raise SystemExit('missing regular source input: ' + str(original))
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)

    check = subprocess.run([str(git), '-C', str(root), 'apply', '--check',
                            '-p1', str(patch)], capture_output=True, text=True)
    if check.returncode:
        raise SystemExit('exact recipe patch does not apply: ' +
                         check.stdout + check.stderr)
    applied = subprocess.run([str(git), '-C', str(root), 'apply', '-p1', str(patch)],
                             capture_output=True, text=True)
    if applied.returncode:
        raise SystemExit('exact recipe patch failed to apply: ' +
                         applied.stdout + applied.stderr)

    include = root / 'mock-include'
    (include / 'build').mkdir(parents=True)
    (include / 'Availability.h').write_text(
        '/* deployment versions supplied by the matrix */\n')
    (include / 'build/build_config.h').write_text(
        '#define BUILDFLAG(flag) TEST_##flag\n')
    probe = root / 'probe.c'
    probe.write_text(
        '#include "net/base/network_change_notifier_apple_buildflags.h"\n'
        '#if EXPECT_LEGACY\n'
        '#ifndef COMPILE_OLD_NOTIFIER_IMPL\n'
        '#error expected legacy implementation\n'
        '#endif\n'
        '#else\n'
        '#ifdef COMPILE_OLD_NOTIFIER_IMPL\n'
        '#error unexpected legacy implementation\n'
        '#endif\n'
        '#endif\n'
        'int network_change_buildflag_probe;\n')

    for name, is_mac, is_ios, is_tvos, versions, expect_legacy in cases:
        argv = [str(clang), '-E', '-x', 'c', '-I', str(include), '-I', str(root),
                '-DTEST_IS_MAC=' + str(is_mac), '-DTEST_IS_IOS=' + str(is_ios),
                '-DTEST_IS_IOS_TVOS=' + str(is_tvos),
                '-DEXPECT_LEGACY=' + str(expect_legacy)]
        argv += ['-D' + key + '=' + str(value) for key, value in versions.items()]
        argv.append(str(probe))
        result = subprocess.run(argv, capture_output=True, text=True)
        if result.returncode:
            raise SystemExit(name + ' preprocessing failed:\n' +
                             result.stdout + result.stderr)
        print('PASS: ' + name + ' source guard')

    implementation = (root / 'net/base/network_change_notifier_apple.mm').read_text()
    marker = 'bool NetworkChangeNotifierApple::ShouldUseNetworkPathMonitor() const {'
    start = implementation.find(marker)
    if start < 0:
        raise SystemExit('patched production method is missing')
    opening = implementation.find('{', start)
    depth = 0
    end = None
    for index in range(opening, len(implementation)):
        if implementation[index] == '{':
            depth += 1
        elif implementation[index] == '}':
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise SystemExit('patched production method is unbalanced')
    method = implementation[start:end]
    method_source = root / 'method.cc'
    method_source.write_text(
        'namespace base { struct Feature { bool enabled; }; '
        'struct FeatureList { static bool IsEnabled(const Feature& feature) '
        '{ return feature.enabled; } }; }\n'
        'namespace net { namespace features { extern base::Feature '
        'kUseNetworkPathMonitorForNetworkChangeNotifier; } }\n'
        'namespace net { class NetworkChangeNotifierApple { public: '
        'bool ShouldUseNetworkPathMonitor() const; }; }\n'
        'namespace net { namespace features { base::Feature '
        'kUseNetworkPathMonitorForNetworkChangeNotifier = {false}; } }\n'
        'namespace net {\n' + method + '\n' +
        '}\n'
        'int main(int argc, char**) {\n'
        '  net::features::kUseNetworkPathMonitorForNetworkChangeNotifier.enabled = argc > 1;\n'
        '  const bool expected = EXPECT_LEGACY ? argc > 1 : true;\n'
        '  return net::NetworkChangeNotifierApple().ShouldUseNetworkPathMonitor() == expected ? 0 : 1;\n'
        '}\n')
    for name, is_mac, is_ios, is_tvos, versions, expect_legacy in cases:
        binary = root / ('method-' + name.replace(' ', '-').replace('.', '-'))
        compile_argv = [str(clangxx), '--target=' + args.target,
                        '--sysroot=' + str(sysroot),
                        '-mmacosx-version-min=' + args.deployment_target,
                        '-resource-dir=' + str(resource_dir),
                        '--ld-path=' + str(ld_path), '-rtlib=compiler-rt',
                        '-nostdlib++', '-std=c++20', '-Werror',
                        '-fno-exceptions', '-fno-rtti',
                        '-DEXPECT_LEGACY=' + str(expect_legacy)]
        if expect_legacy:
            compile_argv.append('-DCOMPILE_OLD_NOTIFIER_IMPL=1')
        compile_argv += [str(method_source), '-o', str(binary)]
        selected_env = {'PATH': str(host_prefix / 'bin'),
                        'SDKROOT': str(sysroot), 'TMPDIR': str(root)}
        compiled = subprocess.run(compile_argv, capture_output=True, text=True,
                                  env=selected_env)
        if compiled.returncode:
            raise SystemExit(name + ' production-method compile failed:\n' +
                             compiled.stdout + compiled.stderr)
        for enabled in (False, True):
            run = subprocess.run([str(binary)] + (['enabled'] if enabled else []),
                                 capture_output=True, text=True, env=selected_env)
            if run.returncode:
                raise SystemExit(name + ' production-method behavior failed with feature ' +
                                 ('enabled' if enabled else 'disabled'))
        print('PASS: ' + name + ' production method, feature on/off')

print('PASS: exact ordered Ports patch applies; Apple source and method matrices match')
