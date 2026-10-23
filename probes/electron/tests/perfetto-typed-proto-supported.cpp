// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted E12 regression control).
#include <cstdint>
#include <type_traits>
#include <utility>

#include "src/trace_processor/importers/proto/typed_proto_field.h"

namespace {
using Type = protozero::proto_utils::ProtoSchemaType;
using Repetition = protozero::proto_utils::RepetitionType;
using Metadata = protozero::proto_utils::FieldMetadata<
    1, Repetition::kNotRepeated, Type::kInt32, int32_t, void>;
inline constexpr Metadata kMetadata{};
using CastResult = decltype(std::declval<
    perfetto::trace_processor::TypedProtoField const&>().Cast<kMetadata>());
static_assert(std::is_same_v<CastResult, int32_t>);
}  // namespace
