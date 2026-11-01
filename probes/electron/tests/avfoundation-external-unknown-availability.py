#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Apply the exact source patch and compile it against Apple SDK availability."""

import argparse
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

PATCH_NAME = 'avfoundation-external-unknown-macos14.patch'
SOURCE = 'media/base/mac/video_capture_device_avfoundation_helpers.mm'
HEADER = 'media/base/mac/video_capture_device_avfoundation_helpers.h'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True,
                    help='prepared Chromium src before this patch')
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--clangxx', type=Path, required=True)
parser.add_argument('--git', type=Path, required=True)
parser.add_argument('--macos-sdk', type=Path, required=True)
parser.add_argument('--ios-sdk', type=Path, required=True)
args = parser.parse_args()

host = args.host_prefix.resolve(strict=True)
source = args.source.resolve(strict=True)
clangxx = args.clangxx.resolve(strict=True)
git = args.git.resolve(strict=True)
macos_sdk = args.macos_sdk.resolve(strict=True)
ios_sdk = args.ios_sdk.resolve(strict=True)
patch = Path(__file__).resolve().parents[1] / 'patches' / PATCH_NAME
if (not source.is_dir() or not clangxx.is_file() or not git.is_file() or
        not clangxx.is_relative_to(host) or not git.is_relative_to(host) or
        not macos_sdk.is_dir() or not ios_sdk.is_dir() or not patch.is_file()):
    parser.error('source, patch, selected compiler/Git, host prefix and Apple SDKs must exist')

resource_result = subprocess.run([str(clangxx), '-print-resource-dir'],
                                 capture_output=True, text=True, check=True)
resource_dir = Path(resource_result.stdout.strip()).resolve(strict=True)
if not resource_dir.is_relative_to(host):
    parser.error('selected Clang resource directory is outside the native prefix')

env = {'PATH': str(host / 'bin')}

with tempfile.TemporaryDirectory(prefix='avfoundation-availability-') as temporary:
    root = Path(temporary)
    for relative in (SOURCE, HEADER):
        original = source / relative
        if not original.is_file() or original.is_symlink():
            raise SystemExit('missing regular source input: ' + str(original))
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)

    # Supply only unrelated Chromium declarations. The production .mm and its
    # AVFoundation header remain the actual patched inputs under test.
    stubs = {
        'media/base/media_export.h': '#define MEDIA_EXPORT\n',
        'base/debug/crash_logging.h':
            '#define SCOPED_CRASH_KEY_STRING1024(...) do {} while (0)\n',
        'base/debug/dump_without_crashing.h':
            'namespace base { namespace debug { inline void DumpWithoutCrashing() {} } }\n',
        'base/feature_list.h': '''namespace base {
enum FeatureState { FEATURE_ENABLED_BY_DEFAULT };
struct Feature {};
class FeatureList {
 public:
  static bool IsEnabled(const Feature&) { return true; }
};
}
#define BASE_FEATURE(name, state) const base::Feature name{}
''',
        'build/build_config.h': '''#define BUILDFLAG(flag) BUILDFLAG_INTERNAL_##flag()
#define BUILDFLAG_INTERNAL_IS_MAC() TEST_IS_MAC
#define BUILDFLAG_INTERNAL_IS_IOS() TEST_IS_IOS
''',
    }
    for relative, contents in stubs.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)

    def command(case, preprocess=False):
        _, target, sdk, mac, ios, deployment = case
        argv = [str(clangxx), '-x', 'objective-c++', '-fobjc-arc', '-fblocks',
                '-Werror=deprecated-declarations', '-target', target,
                '-isysroot', str(sdk), '-resource-dir', str(resource_dir),
                '-I', str(root), '-DTEST_IS_MAC=' + str(mac),
                '-DTEST_IS_IOS=' + str(ios),
                '-fsyntax-only' if not preprocess else '-E', '-P']
        if target.startswith('arm64-apple-macosx'):
            argv += ['-mmacosx-version-min=' + deployment]
        if not preprocess:
            argv.remove('-P')
        argv.append(str(root / SOURCE))
        return subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True)

    cases = (
        ('macOS 13.0', 'arm64-apple-macosx13.0', macos_sdk, 1, 0, '13.0'),
        ('macOS 14.0', 'arm64-apple-macosx14.0', macos_sdk, 1, 0, '14.0'),
        ('macOS 15.0', 'arm64-apple-macosx15.0', macos_sdk, 1, 0, '15.0'),
        ('iOS 17.0', 'arm64-apple-ios17.0-simulator', ios_sdk, 0, 1, '17.0'),
    )

    mac13 = cases[0]
    baseline13 = command(mac13)
    if baseline13.returncode:
        raise SystemExit('unpatched macOS 13 source unexpectedly failed:\n' +
                         baseline13.stdout + baseline13.stderr)
    print('PASS: unpatched macOS 13 retains the deprecated alias')

    baseline14 = command(cases[1])
    if (baseline14.returncode == 0 or
            'AVCaptureDeviceTypeExternalUnknown' not in baseline14.stderr or
            'deprecated' not in baseline14.stderr):
        raise SystemExit('unpatched macOS 14 did not expose the deprecated API failure:\n' +
                         baseline14.stdout + baseline14.stderr)
    print('PASS: unpatched macOS 14 fails on ExternalUnknown deprecation')

    check = subprocess.run([str(git), '-C', str(root), 'apply', '--check', '-p1', str(patch)],
                           env=env, capture_output=True, text=True)
    if check.returncode:
        raise SystemExit('exact recipe patch does not apply:\n' + check.stdout + check.stderr)
    applied = subprocess.run([str(git), '-C', str(root), 'apply', '-p1', str(patch)],
                             env=env, capture_output=True, text=True)
    if applied.returncode:
        raise SystemExit('exact recipe patch failed to apply:\n' + applied.stdout + applied.stderr)

    for case in cases:
        name, *_ = case
        result = command(case)
        if result.returncode:
            raise SystemExit(name + ' patched compile failed:\n' + result.stdout + result.stderr)
        pp = command(case, preprocess=True)
        if pp.returncode:
            raise SystemExit(name + ' patched preprocess failed:\n' + pp.stdout + pp.stderr)
        marker = 'GetVideoCaptureDevices()'
        start = pp.stdout.rfind(marker)
        end = pp.stdout.find('@try', start)
        if start < 0 or end < 0:
            raise SystemExit(name + ' could not isolate the production function in preprocessor output')
        body = pp.stdout[start:end]
        old = 'AVCaptureDeviceTypeExternalUnknown' in body
        modern = re.search(r'\bAVCaptureDeviceTypeExternal\b', body) is not None
        continuity = 'AVCaptureDeviceTypeContinuityCamera' in body
        if name == 'macOS 13.0' and (not old or not modern or not continuity):
            raise SystemExit(name + ' lost a required legacy or modern camera type')
        if name in ('macOS 14.0', 'macOS 15.0') and (old or not modern or not continuity):
            raise SystemExit(name + ' retained the deprecated alias or lost modern camera types')
        if name == 'iOS 17.0' and (old or modern or continuity):
            raise SystemExit(name + ' unexpectedly compiled the macOS camera-device branch')
        print('PASS: ' + name + ' compile and production-source type selection')
