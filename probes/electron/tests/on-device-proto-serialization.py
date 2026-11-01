#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the production descriptor wrapper's serialization result handling."""

import argparse
import importlib.util
from io import StringIO
import json
import platform
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True,
                    help='prepared Chromium src containing the generator and its Python runtime')
parser.add_argument('--host-prefix', type=Path, required=True,
                    help='selected native prefix containing gpatch and native tools')
parser.add_argument('--native-cxx', type=Path, required=True,
                    help='existing SDK native C++ compiler binding wrapper')
parser.add_argument('--ld64', type=Path, required=True,
                    help='selected native ld64.lld from the host prefix')
parser.add_argument('--macos-sdk', type=Path, required=True,
                    help='macOS SDK recorded by the native C++ binding')
parser.add_argument('--sanitize', action='store_true',
                    help='also run the fixture with selected Clang ASan and UBSan')
args = parser.parse_args()

source = args.source.resolve(strict=True)
prefix = args.host_prefix.resolve(strict=True)
native_cxx = args.native_cxx.resolve(strict=True)
ld64 = args.ld64.resolve(strict=True)
sdk = args.macos_sdk.resolve(strict=True)
generator = source / 'components/optimization_guide/tools/gen_on_device_proto_descriptors.py'
gpatch = prefix / 'bin/gpatch'
protobuf_python = source / 'third_party/protobuf/python'
patch = Path(__file__).resolve().parents[1] / 'patches/optimization-guide-descriptor-serialization-check.patch'
binding_metadata = native_cxx.parent / 'commands.json'
if (not generator.is_file() or not protobuf_python.is_dir() or
        any(not tool.is_file() or not tool.resolve(strict=True).is_relative_to(prefix)
            for tool in (gpatch, ld64)) or
        not binding_metadata.is_file() or
        not patch.is_file()):
    parser.error('source generator, Python protobuf module, patch, native compiler binding and tools must exist')
if not native_cxx.is_file():
    parser.error('selected native C++ compiler binding must be a regular file')
binding = json.loads(binding_metadata.read_text(encoding='utf-8'))
compiler_argv = binding.get('commands', {}).get('cxx', {}).get('argv')
if (not isinstance(compiler_argv, list) or not compiler_argv or
        not isinstance(compiler_argv[0], str) or
        not Path(compiler_argv[0]).resolve(strict=True).is_relative_to(prefix)):
    parser.error('native C++ binding does not select a compiler inside the host prefix')
native_runtime = binding.get('native_cxx_runtime')
if not isinstance(native_runtime, dict):
    parser.error('native compiler binding has no selected C++ runtime')
try:
    runtime_library_dir = Path(native_runtime['library_dir']).resolve(strict=True)
    runtime_include_dir = Path(native_runtime['include_dir']).resolve(strict=True)
    runtime_sysroot = Path(native_runtime['sysroot']).resolve(strict=True)
    deployment = native_runtime['deployment']
    targets = native_runtime['targets']
except (KeyError, TypeError, OSError):
    parser.error('native C++ runtime binding is incomplete')
if (runtime_sysroot != sdk or not runtime_include_dir.is_dir() or
        not runtime_library_dir.is_dir() or not isinstance(deployment, str) or
        not isinstance(targets, list)):
    parser.error('SDK or native runtime paths disagree with compiler binding')
host_arch = {'aarch64': 'arm64', 'amd64': 'x86_64'}.get(
    platform.machine().lower(), platform.machine().lower())
if platform.system() != 'Darwin' or host_arch not in ('arm64', 'x86_64'):
    parser.error('native fixture requires a Darwin arm64 or x86_64 host')
target_prefixes = ('aarch64-', 'arm64-') if host_arch == 'arm64' else ('x86_64-',)
target = next((item for item in targets if isinstance(item, str) and
               item.startswith(target_prefixes)), None)
if target is None:
    parser.error('native C++ runtime has no target for this host architecture')

with tempfile.TemporaryDirectory(prefix='electron-proto-serialization-') as temporary:
    work = Path(temporary)
    env = {
        'PATH': str(prefix / 'bin'),
        'TMPDIR': str(work),
        'SDKROOT': str(sdk),
    }

    def generate(source_root, module_name):
        module_path = source_root / 'components/optimization_guide/tools/gen_on_device_proto_descriptors.py'
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError('cannot load production descriptor generator')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        messages = [
            SimpleNamespace(type_name='fixture.TestMessage',
                            cpp_name='fixture::TestMessage',
                            iname='TestMessage'),
        ]
        output = StringIO()
        module._ConvertValue.GenPublic(output, messages)
        return output.getvalue()

    resource_result = subprocess.run([str(native_cxx), '-print-resource-dir'],
                                     capture_output=True, text=True, check=True, env=env)
    resource = Path(resource_result.stdout.strip()).resolve(strict=True)
    if not resource.is_relative_to(prefix):
        raise SystemExit('selected Clang resource directory is outside native prefix')
    compile_flags = [str(native_cxx), '-std=c++23', '-Werror=unused-result',
                     '--target=' + target, '-arch', host_arch,
                     '-isysroot', str(sdk), '-mmacosx-version-min=' + deployment,
                     '-resource-dir', str(resource), '--ld-path=' + str(ld64),
                     '-Wl,-rpath,' + str(runtime_library_dir),
                     '-I' + str(work)]

    common = '''#include <optional>
#include <string>
#include <utility>

namespace base {
struct Value { bool convert; bool fail_serialization; };
}
namespace proto {
class Any {
 public:
  void set_type_url(std::string value) { type_url_ = std::move(value); }
  std::string* mutable_value() { return &value_; }
  const std::string& type_url() const { return type_url_; }
  const std::string& value() const { return value_; }
 private:
  std::string type_url_;
  std::string value_;
};
}
namespace fixture {
struct TestMessage {
  bool fail_serialization = false;
  [[nodiscard]] bool SerializeToString(std::string* output) const {
    ++serialize_calls;
    *output = fail_serialization ? "partial" : "round-trip";
    return !fail_serialization;
  }
  static int serialize_calls;
};
}

int fixture::TestMessage::serialize_calls = 0;
bool ConvertTestMessage(const base::Value& value, fixture::TestMessage& message) {
  message.fail_serialization = value.fail_serialization;
  return value.convert;
}
'''
    main = '''
int main() {
  auto success = ConvertToAnyWrappedProto(
      base::Value{true, false}, "fixture.TestMessage");
  if (!success || success->type_url() !=
                      "type.googleapis.com/fixture.TestMessage" ||
      success->value() != "round-trip")
    return 1;
  if (fixture::TestMessage::serialize_calls != 1)
    return 2;

  auto failure = ConvertToAnyWrappedProto(
      base::Value{true, true}, "fixture.TestMessage");
  if (failure || fixture::TestMessage::serialize_calls != 2)
    return 3;

  auto conversion_failure = ConvertToAnyWrappedProto(
      base::Value{false, false}, "fixture.TestMessage");
  if (conversion_failure || fixture::TestMessage::serialize_calls != 2)
    return 4;
  if (ConvertToAnyWrappedProto(base::Value{true, false}, "fixture.UnknownMessage"))
    return 5;
  return 0;
}
'''

    baseline_root = work / 'baseline-src'
    baseline_generator = baseline_root / 'components/optimization_guide/tools/gen_on_device_proto_descriptors.py'
    baseline_generator.parent.mkdir(parents=True)
    baseline_generator.write_bytes(generator.read_bytes())
    (baseline_root / 'third_party/protobuf').mkdir(parents=True)
    (baseline_root / 'third_party/protobuf/python').symlink_to(protobuf_python, target_is_directory=True)
    reversed_patch = subprocess.run([str(gpatch), '-R', '-p1', '-d', str(baseline_root)],
                                    input=patch.read_text(encoding='utf-8'),
                                    text=True, capture_output=True, env=env)
    if reversed_patch.returncode:
        raise SystemExit('cannot make isolated baseline generator:\n' +
                         reversed_patch.stdout + reversed_patch.stderr)
    baseline_harness = work / 'baseline-wrapper.cc'
    baseline_harness.write_text(common + generate(baseline_root, 'baseline_generator') + main,
                                 encoding='utf-8')
    baseline_command = compile_flags + [str(baseline_harness),
                                        '-o', str(work / 'baseline-wrapper')]
    baseline = subprocess.run(baseline_command, capture_output=True, text=True, env=env)
    baseline_output = baseline.stdout + baseline.stderr
    if baseline.returncode == 0 or 'unused-result' not in baseline_output:
        raise SystemExit('unpatched emitted wrapper did not fail on ignored nodiscard result:\n' +
                         baseline_output)

    wrapper_harness = work / 'wrapper-test.cc'
    wrapper_harness.write_text(common + generate(source, 'patched_generator') + main,
                               encoding='utf-8')
    binary = work / 'wrapper-test'
    subprocess.run(compile_flags + [str(wrapper_harness), '-o', str(binary)],
                   check=True, env=env)
    subprocess.run([str(binary)], check=True, env=env)
    if args.sanitize:
        sanitized = work / 'wrapper-test-sanitized'
        subprocess.run(compile_flags + ['-fsanitize=address,undefined',
                                        '-fno-omit-frame-pointer',
                                        str(wrapper_harness),
                                        '-o', str(sanitized)],
                       check=True, env=env)
        sanitizer_env = dict(
            env,
            ASAN_OPTIONS='halt_on_error=1:abort_on_error=1:detect_leaks=1',
            UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',
        )
        subprocess.run([str(sanitized)], check=True, env=sanitizer_env)

print('PASS: baseline nodiscard diagnostic; emitted wrapper success, serializer false, conversion false, and unknown type')
if args.sanitize:
    print('PASS: emitted-wrapper fixture ASan/UBSan')
