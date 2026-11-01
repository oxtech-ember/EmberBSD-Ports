#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Compile the production matcher with small callbacks to check order state."""

import argparse
import json
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

PATCH_NAME = 'ca-renderer-layer-tree-initialize-match-order.patch'
SOURCE = 'ui/accelerated_widget_mac/ca_renderer_layer_tree.mm'
MARKER = 'void CARendererLayerTree::MatchLayersToOldTree(CARendererLayerTree* old_tree) {'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True,
                    help='prepared Chromium src before the match-order patch')
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--clangxx', type=Path, required=True)
parser.add_argument('--ld64', type=Path, required=True)
parser.add_argument('--git', type=Path, required=True)
parser.add_argument('--macos-sdk', type=Path, required=True)
args = parser.parse_args()

repo = Path(__file__).resolve().parents[1]
host = args.host_prefix.resolve(strict=True)
source = args.source.resolve(strict=True)
clangxx = args.clangxx.resolve(strict=True)
ld64 = args.ld64.resolve(strict=True)
git = args.git.resolve(strict=True)
sdk = args.macos_sdk.resolve(strict=True)
patch = repo / 'patches' / PATCH_NAME
series_path = repo / 'electron44/files/source-series.json'
if (not source.is_dir() or not clangxx.is_file() or not ld64.is_file() or
        not git.is_file() or not clangxx.is_relative_to(host) or
        not ld64.is_relative_to(host) or not git.is_relative_to(host) or
        not sdk.is_dir() or not patch.is_file() or not series_path.is_file()):
    parser.error('source, patch, selected tools, host prefix and Apple SDK must exist')

series = json.loads(series_path.read_text(encoding='utf-8'))
matches = [entry for entry in series['patches'] if entry.get('path') == PATCH_NAME]
if len(matches) != 1 or matches[0] != {'path': PATCH_NAME, 'root': '', 'strip': 1}:
    parser.error('match-order patch must appear exactly once in the ordered source series')

source_file = source / SOURCE
if not source_file.is_file() or source_file.is_symlink():
    parser.error('missing regular production source: ' + str(source_file))
original = source_file.read_text(encoding='utf-8')
if original.count(MARKER) != 1:
    parser.error('production MatchLayersToOldTree definition is missing or ambiguous')

STUBS = r'''
struct CALayerMap { bool empty() const { return true; } };
struct WeakFactory { void* GetWeakPtr() { return this; } };
struct ContentLayer {
  bool has_iosurface;
  int expected_previous;
  int expected_order;
  int* failures;
  void UpdateMapAndMatchOldLayers(CALayerMap&, int& layer_order,
                                  int& last_old_layer_order) {
    if (!has_iosurface)
      return;
    const int current_order = ++layer_order;
    if (last_old_layer_order != expected_previous ||
        current_order != expected_order)
      ++*failures;
    last_old_layer_order = current_order;
  }
};
template <typename T> struct LayerList {
  T* first;
  T* last;
  T* begin() { return first; }
  T* end() { return last; }
};
struct TransformLayer { LayerList<ContentLayer> content_layers_; };
struct ClipAndSortingLayer { LayerList<TransformLayer> transform_layers_; };
struct RootLayer {
  void* old_layer_ = 0;
  WeakFactory weak_factory_for_new_layer_;
  LayerList<ClipAndSortingLayer> clip_and_sorting_layers_;
  void CALayerFallBack() {}
};
struct CARendererLayerTree {
  bool has_committed_ = true;
  float scale_factor_ = 1.0f;
  RootLayer root_layer_;
  CALayerMap ca_layer_map_;
  void MatchLayersToOldTree(CARendererLayerTree* old_tree);
};
struct DcheckProxy {
  template <typename T> DcheckProxy& operator<<(const T&) { return *this; }
};
#define DCHECK(expression) DcheckProxy()
'''

def extract_function(text):
    start = text.index(MARKER)
    opening = text.index('{', start)
    depth = 0
    for offset in range(opening, len(text)):
        if text[offset] == '{':
            depth += 1
        elif text[offset] == '}':
            depth -= 1
            if depth == 0:
                return text[start:offset + 1]
    raise SystemExit('unterminated production matcher definition')


MAIN = r'''
int run_case(ContentLayer* layers, int count) {
  int failures = 0;
  for (int index = 0; index < count; ++index)
    layers[index].failures = &failures;
  TransformLayer transform_layers[1] = {{layers, layers + count}};
  ClipAndSortingLayer clip_layers[1] = {{transform_layers, transform_layers + 1}};
  CARendererLayerTree old_tree;
  CARendererLayerTree tree;
  tree.root_layer_.clip_and_sorting_layers_ = {clip_layers, clip_layers + 1};
  tree.MatchLayersToOldTree(&old_tree);
  return failures;
}

int main() {
  ContentLayer first[1] = {{true, 0, 1, 0}};
  if (run_case(first, 1) != 0)
    return 1;
  ContentLayer skipped[2] = {{false, 0, 0, 0}, {true, 0, 1, 0}};
  if (run_case(skipped, 2) != 0)
    return 2;
  ContentLayer sequential[3] = {
      {true, 0, 1, 0}, {true, 1, 2, 0}, {true, 2, 3, 0}};
  if (run_case(sequential, 3) != 0)
    return 3;
  return 0;
}
'''

env = {'PATH': str(host / 'bin'),
       'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())}
resource = Path(subprocess.run([str(clangxx), '-print-resource-dir'],
                               capture_output=True, text=True, check=True).stdout.strip())
resource = resource.resolve(strict=True)
if not resource.is_relative_to(host):
    parser.error('selected Clang resource directory is outside the host prefix')
sdk_settings = json.loads((sdk / 'SDKSettings.json').read_text(encoding='utf-8'))
sdk_version = sdk_settings.get('Version')
if not isinstance(sdk_version, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', sdk_version):
    parser.error('selected macOS SDK has no numeric version in SDKSettings.json')
host_arch = {'aarch64': 'arm64', 'amd64': 'x86_64'}.get(
    platform.machine().lower(), platform.machine().lower())
if host_arch not in ('arm64', 'x86_64'):
    parser.error('matcher regression requires an arm64 or x86_64 Darwin host')

with tempfile.TemporaryDirectory(prefix='ca-renderer-match-order-') as temporary:
    temp = Path(temporary)
    copied = temp / SOURCE
    copied.parent.mkdir(parents=True)
    shutil.copyfile(source_file, copied)
    check = subprocess.run([str(git), 'apply', '--check', '-p1', str(patch)],
                           cwd=temp, env=env, capture_output=True, text=True)
    if check.returncode:
        raise SystemExit('exact recipe patch does not apply:\n' + check.stdout + check.stderr)

    def build_and_run(label, source_text, *, expected_status):
        fixture = temp / 'match-order.cc'
        fixture.write_text(STUBS + '\n' + extract_function(source_text) + '\n' + MAIN,
                           encoding='utf-8')
        binary = temp / ('match-order-' + label)
        command = [str(clangxx), '-std=c++17', '-ftrivial-auto-var-init=pattern',
                   '-fuse-ld=' + str(ld64), '-nostdlib++', '-isysroot', str(sdk),
                   '-target', host_arch + '-apple-macosx14.0', '-arch', host_arch,
                   '-mmacosx-version-min=14.0', '-resource-dir', str(resource),
                   '-Wl,-platform_version,macos,14.0,' + sdk_version,
                   str(fixture), '-o', str(binary)]
        result = subprocess.run(command, cwd=temp, env=env,
                                capture_output=True, text=True)
        if result.returncode:
            raise SystemExit(label + ' compile failed:\n' + result.stdout + result.stderr)
        run = subprocess.run([str(binary)], cwd=temp, env=env,
                             capture_output=True, text=True)
        if run.returncode != expected_status:
            raise SystemExit(label + ' returned status ' + str(run.returncode) +
                             ', expected ' + str(expected_status) + '\n' +
                             run.stdout + run.stderr)
        print('PASS: ' + label)

    build_and_run('baseline fails deterministically', original, expected_status=1)
    applied = subprocess.run([str(git), 'apply', '-p1', str(patch)], cwd=temp,
                             env=env, capture_output=True, text=True)
    if applied.returncode:
        raise SystemExit('exact recipe patch failed to apply:\n' +
                         applied.stdout + applied.stderr)
    patched = copied.read_text(encoding='utf-8')
    build_and_run('patched first, skipped-first and sequential matches',
                  patched, expected_status=0)
