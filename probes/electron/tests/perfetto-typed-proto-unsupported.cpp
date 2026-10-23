// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted E12 regression control).
#include <cstdint>

#include "src/trace_processor/importers/proto/typed_proto_field.h"

using Type = protozero::proto_utils::ProtoSchemaType;
using Repetition = protozero::proto_utils::RepetitionType;
#ifndef PERFETTO_TEST_SCHEMA_TYPE
#define PERFETTO_TEST_SCHEMA_TYPE Type::kUnknown
#endif
using Metadata = protozero::proto_utils::FieldMetadata<
    1, Repetition::kNotRepeated, PERFETTO_TEST_SCHEMA_TYPE, int32_t, void>;
inline constexpr Metadata kMetadata{};
void instantiate(perfetto::trace_processor::TypedProtoField const& field) {
  (void)field.Cast<kMetadata>();
}
