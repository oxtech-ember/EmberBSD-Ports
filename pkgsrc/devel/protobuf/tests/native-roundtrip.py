#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise a staged native Protobuf package with the selected runtime."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('host-prefix', 'stage-prefix', 'package-prefix', 'cxx', 'macos-sdk',
             'macos-minimum', 'work-dir'):
    parser.add_argument('--' + name, required=True)
args = parser.parse_args()
host, stage, package = map(Path, (args.host_prefix, args.stage_prefix, args.package_prefix))
for path in (host, stage, package, Path(args.cxx), Path(args.macos_sdk), Path(args.work_dir)):
    if not path.is_absolute():
        parser.error('paths must be absolute')

with tempfile.TemporaryDirectory(prefix='protobuf-native-roundtrip-', dir=args.work_dir) as tmp:
    work = Path(tmp)
    view = work / 'lib'
    view.mkdir()
    for directory, patterns in ((stage / 'lib', ('libabsl_*.dylib',)),
                                (stage / 'lib/libc++', ('libc++_ember1*.dylib',)),
                                (package / 'lib', ('libprotobuf*.dylib', 'libprotoc*.dylib',
                                                   'libutf8*.dylib'))):
        for pattern in patterns:
            for source in directory.glob(pattern):
                target = view / source.name
                if not target.exists():
                    target.symlink_to(source.resolve(strict=True))
    env = {'PATH': str(host / 'bin') + ':' + str(host / 'sbin'),
           'PKG_CONFIG_LIBDIR': str(package / 'lib/pkgconfig') + ':' + str(stage / 'lib/pkgconfig'),
           'DYLD_LIBRARY_PATH': str(view)}
    def run(command, environment=env):
        return subprocess.run([str(x) for x in command], env=environment, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    (work / 'test.proto').write_text('syntax = "proto3"; package ember_probe; '
                                     'message Sample { string text = 1; int32 value = 2; }\n')
    (work / 'test.cc').write_text('''#include "test.pb.h"
#include <cassert>
#include <string>
int main() {
  ember_probe::Sample message;
  message.set_text("hello");
  message.set_value(42);
  std::string encoded;
  assert(message.SerializeToString(&encoded));
  std::string output = "prefix";
  assert(message.AppendToString(&output) && output == "prefix" + encoded);
  ember_probe::Sample restored;
  assert(restored.ParseFromString(output.substr(6)));
  assert(restored.text() == "hello" && restored.value() == 42);
  ember_probe::Sample empty;
  std::string empty_out = "prefix";
  assert(empty.AppendToString(&empty_out) && empty_out == "prefix");
}
''')
    run([package / 'bin/protoc', '--proto_path=' + str(work), '--cpp_out=' + str(work),
         work / 'test.proto'])
    flags = shlex.split(run([host / 'bin/pkgconf', '--libs', 'protobuf']).stdout)
    flags = [flag for flag in flags if not flag.startswith('-L')]
    run([args.cxx, '-isysroot', args.macos_sdk, '-mmacos-version-min=' + args.macos_minimum,
         '-std=c++20', '-DPROTOBUF_USE_DLLS', '-I' + str(work), '-I' + str(package / 'include'),
         '-I' + str(stage / 'include'), work / 'test.cc', work / 'test.pb.cc',
         '-L' + str(package / 'lib'), '-L' + str(stage / 'lib'), *flags, '-o', work / 'test'])
    result = run([work / 'test'], dict(env, DYLD_PRINT_LIBRARIES='1'))
    for library in ((stage / 'lib/libc++/libc++_ember1.1.dylib').resolve(strict=True).name,
                    (package / 'lib/libprotobuf.dylib').resolve(strict=True).name, 'libabsl_'):
        if library not in result.stderr:
            raise AssertionError('expected staged library not loaded: ' + library)
print('native Protobuf prefix append, empty, roundtrip and staged ABI PASS')
