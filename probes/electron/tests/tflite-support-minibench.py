#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the actual Support guard and initializer state with a bounded stub."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--cxx', required=True)
parser.add_argument('--wrapper', type=Path, required=True)
args = parser.parse_args()
source = args.wrapper.read_text()
start = source.index('  // Store interpreter initializer if not already here.')
end = source.index('  // Sanity check and copy ComputeSettings.', start)
guard = source[start:end]
program = r'''#include <functional>
#include <utility>
#include <cassert>
namespace absl {
struct Status { int code; };
Status UnimplementedError(const char*) { return {1}; }
Status FailedPreconditionError(const char*) { return {2}; }
}
struct ComputeSettings { bool benchmark; bool has_settings_to_test_locally() const { return benchmark; } };
struct Wrapper {
  std::function<void()> interpreter_initializer_;
  absl::Status InitializeWithFallback(std::function<void()> interpreter_initializer,
                                      const ComputeSettings& compute_settings) {
''' + guard + r'''    interpreter_initializer_();
    return {0};
  }
};
int main() {
  int calls = 0;
  Wrapper first;
  assert(first.InitializeWithFallback([&] { ++calls; }, {true}).code == 1);
  assert(calls == 0 && !first.interpreter_initializer_);
  assert(first.InitializeWithFallback([&] { ++calls; }, {false}).code == 0);
  assert(calls == 1 && first.interpreter_initializer_);
  Wrapper normal;
  assert(normal.InitializeWithFallback([&] { ++calls; }, {false}).code == 0);
  assert(calls == 2);
  assert(normal.InitializeWithFallback([&] { ++calls; }, {true}).code == 2);
  assert(calls == 2);
}
'''
with tempfile.TemporaryDirectory(prefix='support-minibench-') as tmp:
    root = Path(tmp)
    path = root / 'guard.cc'
    path.write_text(program)
    subprocess.run([args.cxx, '-std=c++17', str(path), '-o', str(root / 'guard')], check=True)
    subprocess.run([str(root / 'guard')], check=True)
print('PASS: production guard rejects benchmark before state, default and retry continue (stubbed initializer)')
