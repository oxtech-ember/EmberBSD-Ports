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
                                     'enum Kind { option allow_alias = true; ZERO = 0; ALIAS = 0; POSITIVE = 7; NEGATIVE = -5; } '
                                     'message Sample { string text = 1; int32 value = 2; '
                                     'Kind kind = 3; repeated Kind kinds = 4; }\n')
    (work / 'closed.proto').write_text('syntax = "proto2"; package ember_probe; '
                                       'import "test.proto"; message Closed { '
                                       'optional Kind kind = 1; repeated Kind kinds = 2; }\n')
    (work / 'test.cc').write_text('''#include "test.pb.h"
#include "closed.pb.h"
#include <google/protobuf/unknown_field_set.h>
#include <google/protobuf/reflection_ops.h>
#include <google/protobuf/text_format.h>
#include <google/protobuf/util/field_mask_util.h>
#include <google/protobuf/util/message_differencer.h>
#include <cassert>
#include <cstddef>
#include <string>
#include <utility>
namespace google::protobuf::internal {
class UnsetFieldsMetadataTextFormatTestUtil {
 public:
  static size_t Count(const TextFormat::Parser::UnsetFieldsMetadata& data) {
    return data.ids_.size();
  }
};
}
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
  google::protobuf::UnknownFieldSet unknown;
  unknown.AddVarint(3, 150);
  std::string unknown_bytes = "old contents";
  assert(unknown.SerializeToString(&unknown_bytes));
  google::protobuf::UnknownFieldSet parsed_unknown;
  assert(parsed_unknown.ParseFromString(unknown_bytes));
  assert(parsed_unknown.field_count() == 1 && parsed_unknown.field(0).number() == 3);
  assert(parsed_unknown.field(0).varint() == 150);
  unknown.Clear();
  assert(unknown.SerializeToString(&unknown_bytes) && unknown_bytes.empty());
  const auto* descriptor = message.GetDescriptor();
  const auto* singular = descriptor->FindFieldByName("kind");
  const auto* repeated = descriptor->FindFieldByName("kinds");
  const auto* reflection = message.GetReflection();
  for (int value : {7, -5, 123, -42}) {
    message.Clear();
    reflection->SetEnumValue(&message, singular, value);
    reflection->AddEnumValue(&message, repeated, value);
    assert(message.SerializeToString(&encoded));
    assert(restored.ParseFromString(encoded));
    assert(reflection->GetEnumValue(restored, singular) == value);
    assert(reflection->GetRepeatedEnumValue(restored, repeated, 0) == value);
    assert(google::protobuf::util::MessageDifferencer::Equals(message, restored));
  }
  reflection->SetEnumValue(&message, singular, 123);
  const auto* unknown_enum = reflection->GetEnum(message, singular);
  ember_probe::Closed closed;
  const auto* closed_reflection = closed.GetReflection();
  const auto* closed_kind = closed.GetDescriptor()->FindFieldByName("kind");
  const auto* closed_kinds = closed.GetDescriptor()->FindFieldByName("kinds");
  assert(closed_kind->enum_type() == singular->enum_type());
  assert(closed_kind->legacy_enum_field_treated_as_closed());
  closed_reflection->SetEnum(&closed, closed_kind, unknown_enum);
  closed_reflection->AddEnum(&closed, closed_kinds, unknown_enum);
  assert(closed_reflection->GetEnumValue(closed, closed_kind) == 123);
  ember_probe::Closed merged;
  google::protobuf::internal::ReflectionOps::Merge(closed, &merged);
  assert(closed_reflection->GetEnumValue(merged, closed_kind) == 123);
  assert(closed_reflection->GetRepeatedEnumValue(merged, closed_kinds, 0) == 123);
  google::protobuf::FieldMask mask;
  mask.add_paths("kind");
  mask.add_paths("kinds");
  google::protobuf::util::FieldMaskUtil::MergeOptions options;
  ember_probe::Closed destination;
  closed_reflection->AddEnumValue(&destination, closed_kinds, 7);
  google::protobuf::util::FieldMaskUtil::MergeMessageTo(closed, mask, options, &destination);
  assert(closed_reflection->GetEnumValue(destination, closed_kind) == 123);
  assert(closed_reflection->FieldSize(destination, closed_kinds) == 2);
  assert(closed_reflection->GetRepeatedEnumValue(destination, closed_kinds, 1) == 123);
  options.set_replace_repeated_fields(true);
  google::protobuf::util::FieldMaskUtil::MergeMessageTo(closed, mask, options, &destination);
  assert(closed_reflection->FieldSize(destination, closed_kinds) == 1);
  assert(closed_reflection->GetRepeatedEnumValue(destination, closed_kinds, 0) == 123);
  closed_reflection->ClearField(&closed, closed_kind);
  google::protobuf::util::FieldMaskUtil::MergeMessageTo(closed, mask, options, &destination);
  assert(!closed_reflection->HasField(destination, closed_kind));
  for (const auto& entry : {std::pair<const char*, size_t>{"kind: ZERO", 1},
                            {"kind: ALIAS", 0}}) {
    ember_probe::Sample parsed;
    google::protobuf::TextFormat::Parser parser;
    google::protobuf::TextFormat::Parser::UnsetFieldsMetadata metadata;
    parser.OutputNoOpFields(&metadata);
    assert(parser.ParseFromString(entry.first, &parsed));
    assert(google::protobuf::internal::UnsetFieldsMetadataTextFormatTestUtil::Count(metadata) == entry.second);
  }
}
''')
    run([package / 'bin/protoc', '--proto_path=' + str(work), '--cpp_out=' + str(work),
         work / 'test.proto', work / 'closed.proto'])
    flags = shlex.split(run([host / 'bin/pkgconf', '--libs', 'protobuf']).stdout)
    flags = [flag for flag in flags if not flag.startswith('-L')]
    run([args.cxx, '-isysroot', args.macos_sdk, '-mmacos-version-min=' + args.macos_minimum,
         '-std=c++20', '-DPROTOBUF_USE_DLLS', '-I' + str(work), '-I' + str(package / 'include'),
         '-I' + str(stage / 'include'), work / 'test.cc', work / 'test.pb.cc', work / 'closed.pb.cc',
         '-L' + str(package / 'lib'), '-L' + str(stage / 'lib'), *flags, '-o', work / 'test'])
    result = run([work / 'test'], dict(env, DYLD_PRINT_LIBRARIES='1'))
    for library in ((stage / 'lib/libc++/libc++_ember1.1.dylib').resolve(strict=True).name,
                    (package / 'lib/libprotobuf.dylib').resolve(strict=True).name, 'libabsl_'):
        if library not in result.stderr:
            raise AssertionError('expected staged library not loaded: ' + library)
print('native Protobuf prefix append, unknown fields, roundtrip and staged ABI PASS')
