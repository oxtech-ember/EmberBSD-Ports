#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Apply the Electron patch and compile its production availability branch."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

PATCH_NAME = 'ca-renderer-layer-tree-macos14-sample-buffer-renderer.patch'
SOURCE = 'ui/accelerated_widget_mac/ca_renderer_layer_tree.mm'
BEGIN = '  if (@available(macOS 14, iOS 17, *)) {'
END = '\n  }\n\n  switch (status)'
MODERN = '  AVSampleBufferVideoRenderer* renderer = av_layer.sampleBufferRenderer;'
END_MODERN = '\n\n  switch (status)'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True,
                    help='prepared Chromium src before this patch')
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--clangxx', type=Path, required=True)
parser.add_argument('--git', type=Path, required=True)
parser.add_argument('--macos-sdk', type=Path, required=True)
args = parser.parse_args()

host = args.host_prefix.resolve(strict=True)
source = args.source.resolve(strict=True)
clangxx = args.clangxx.resolve(strict=True)
git = args.git.resolve(strict=True)
sdk = args.macos_sdk.resolve(strict=True)
patch = Path(__file__).resolve().parents[1] / 'patches' / PATCH_NAME
series_path = Path(__file__).resolve().parents[1] / '../../pkgsrc/devel/electron44/files/source-series.json'
if (not source.is_dir() or not clangxx.is_file() or not git.is_file() or
        not clangxx.is_relative_to(host) or not git.is_relative_to(host) or
        not sdk.is_dir() or not patch.is_file() or not series_path.is_file()):
    parser.error('source, patch, selected compiler/Git, host prefix and Apple SDK must exist')

series = json.loads(series_path.read_text(encoding='utf-8'))
registered = [row for row in series['patches'] if row.get('path') == PATCH_NAME]
if len(registered) != 1 or registered[0] != {'path': PATCH_NAME, 'root': '', 'strip': 1}:
    parser.error('patch must be registered exactly once in the ordered source series')

resource_result = subprocess.run([str(clangxx), '-print-resource-dir'],
                                 capture_output=True, text=True, check=True)
resource_dir = Path(resource_result.stdout.strip()).resolve(strict=True)
if not resource_dir.is_relative_to(host):
    parser.error('selected Clang resource directory is outside the native prefix')

env = {'PATH': str(host / 'bin')}
input_file = source / SOURCE
if not input_file.is_file() or input_file.is_symlink():
    parser.error('missing regular production source: ' + str(input_file))
if input_file.read_text(encoding='utf-8').count(BEGIN) != 1:
    parser.error('production source availability block is missing or ambiguous')

def wrapper(source_block):
    return '''#import <AVFoundation/AVFoundation.h>
void check_renderer(AVSampleBufferDisplayLayer* av_layer,
                    CMSampleBufferRef input_sample_buffer) {
  struct BufferRef {
    CMSampleBufferRef value;
    CMSampleBufferRef get() const { return value; }
  } wrapped{input_sample_buffer};
  auto& sample_buffer = wrapped;
  AVQueuedSampleBufferRenderingStatus status;
  NSError* error;
  int source_begin_marker = 314159;
''' + source_block + '''
  int source_end_marker = 271828;
  (void)source_begin_marker;
  (void)source_end_marker;
  if (status == AVQueuedSampleBufferRenderingStatusFailed && error != nil) {
  }
}
'''

def compile_block(path, version, *, preprocess=False):
    target = 'arm64-apple-macosx' + version
    command = [str(clangxx), '-x', 'objective-c++', '-fobjc-arc', '-fblocks',
               '-Werror=deprecated-declarations', '-Werror=unguarded-availability-new',
               '-target', target,
               '-isysroot', str(sdk), '-resource-dir', str(resource_dir)]
    command += ['-E', '-P'] if preprocess else ['-fsyntax-only']
    command.append(str(path))
    return subprocess.run(command, cwd=path.parent, env=env,
                          capture_output=True, text=True)

with tempfile.TemporaryDirectory(prefix='ca-renderer-availability-') as temporary:
    root = Path(temporary)
    copied = root / SOURCE
    copied.parent.mkdir(parents=True)
    shutil.copyfile(input_file, copied)
    before = copied.read_text(encoding='utf-8')
    before_start = before.index(BEGIN)
    before_end = before.index(END, before_start) + len('\n  }')
    unpatched_block = before[before_start:before_end]
    fixture = root / 'availability.mm'
    fixture.write_text(wrapper(unpatched_block), encoding='utf-8')

    for version in ('13.0', '14.0'):
        result = compile_block(fixture, version)
        if result.returncode:
            raise SystemExit('unpatched macOS ' + version + ' unexpectedly failed:\n' +
                             result.stdout + result.stderr)
        print('PASS: unpatched macOS ' + version + ' compiles')

    baseline15 = compile_block(fixture, '15.0')
    if (baseline15.returncode == 0 or
            'enqueueSampleBuffer:' not in baseline15.stderr or
            'deprecated' not in baseline15.stderr):
        raise SystemExit('unpatched macOS 15 did not expose the deprecated fallback:\n' +
                         baseline15.stdout + baseline15.stderr)
    print('PASS: unpatched macOS 15 fails on the deprecated fallback')

    check = subprocess.run([str(git), 'apply', '--check', '-p1', str(patch)],
                           cwd=root, env=env, capture_output=True, text=True)
    if check.returncode:
        raise SystemExit('exact recipe patch does not apply:\n' + check.stdout + check.stderr)
    applied = subprocess.run([str(git), 'apply', '-p1', str(patch)],
                             cwd=root, env=env, capture_output=True, text=True)
    if applied.returncode:
        raise SystemExit('exact recipe patch failed to apply:\n' +
                         applied.stdout + applied.stderr)
    patched_text = copied.read_text(encoding='utf-8')
    if patched_text.count(MODERN) != 1:
        raise SystemExit('patched source does not contain one modern renderer path')
    patched_start = patched_text.index(MODERN)
    patched_end = patched_text.index(END_MODERN, patched_start)
    patched_block = patched_text[patched_start:patched_end]
    fixture.write_text(wrapper(patched_block), encoding='utf-8')

    minimum13 = compile_block(fixture, '13.0')
    if (minimum13.returncode == 0 or 'available' not in minimum13.stderr or
            'macOS 14' not in minimum13.stderr):
        raise SystemExit('macOS 13 did not reject the macOS 14-only renderer API:\n' +
                         minimum13.stdout + minimum13.stderr)
    print('PASS: patched macOS 13 rejects the unavailable renderer API')

    for version in ('14.0', '15.0'):
        result = compile_block(fixture, version)
        if result.returncode:
            raise SystemExit('patched macOS ' + version + ' compile failed:\n' +
                             result.stdout + result.stderr)
        pp = compile_block(fixture, version, preprocess=True)
        if pp.returncode:
            raise SystemExit('macOS ' + version + ' preprocess failed:\n' +
                             pp.stdout + pp.stderr)
        begin_marker = pp.stdout.rfind('source_begin_marker = 314159')
        end_marker = pp.stdout.find('source_end_marker = 271828', begin_marker)
        if begin_marker < 0 or end_marker < 0:
            raise SystemExit('macOS ' + version + ' cannot isolate production block')
        body = pp.stdout[begin_marker:end_marker]
        modern = '[renderer enqueueSampleBuffer:' in body
        legacy = '[av_layer enqueueSampleBuffer:' in body or 'av_layer.status' in body or 'av_layer.error' in body
        if not modern or legacy:
            raise SystemExit('macOS ' + version + ' selected the wrong production API')
        print('PASS: patched macOS ' + version + ' compile and API selection')
