// Copyright 2026 The EmberBSD Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <cstdint>
#include <cstdio>
#include <limits>
#include <type_traits>

#include "services/tracing/public/mojom/console_config_mojom_traits.h"
#include "services/tracing/public/mojom/trace_config_mojom_traits.h"

namespace {
using Console = perfetto::protos::gen::ConsoleConfig;
using Buffer = perfetto::TraceConfig::BufferConfig;
using ConsoleWire = tracing::mojom::ConsoleOutput;
using BufferWire = tracing::mojom::BufferFillPolicy;
static_assert(std::is_same_v<std::underlying_type_t<Console::Output>, int>);
static_assert(std::is_same_v<std::underlying_type_t<Buffer::FillPolicy>, int>);
static_assert(std::is_same_v<std::underlying_type_t<ConsoleWire>, int32_t>);
static_assert(std::is_same_v<std::underlying_type_t<BufferWire>, int32_t>);
static_assert(std::numeric_limits<int>::min() == std::numeric_limits<int32_t>::min());
static_assert(std::numeric_limits<int>::max() == std::numeric_limits<int32_t>::max());
static_assert(Console::OUTPUT_UNSPECIFIED == 0 && Console::OUTPUT_STDOUT == 1 && Console::OUTPUT_STDERR == 2);
static_assert(Buffer::UNSPECIFIED == 0 && Buffer::RING_BUFFER == 1 && Buffer::DISCARD == 2);
static_assert(static_cast<int32_t>(ConsoleWire::kOutputUnspecified) == 0 && static_cast<int32_t>(ConsoleWire::kOutputStdOut) == 1 && static_cast<int32_t>(ConsoleWire::kOutputStdErr) == 2);
static_assert(static_cast<int32_t>(BufferWire::kUnspecified) == 0 && static_cast<int32_t>(BufferWire::kRingBuffer) == 1 && static_cast<int32_t>(BufferWire::kDiscard) == 2);

bool Check(int32_t value) {
  int32_t console = 17;
  int32_t buffer = 17;
  mojo::internal::Serializer<ConsoleWire, Console::Output>::Serialize(static_cast<Console::Output>(value), &console);
  mojo::internal::Serializer<BufferWire, Buffer::FillPolicy>::Serialize(static_cast<Buffer::FillPolicy>(value), &buffer);
  const bool known = value >= 0 && value <= 2;
  return console == value && buffer == value &&
      tracing::mojom::internal::ConsoleOutput_Data::IsKnownValue(console) == known &&
      tracing::mojom::internal::BufferFillPolicy_Data::IsKnownValue(buffer) == known;
}
}  // namespace

int main() {
  const int32_t cases[] = {0, 1, 2, -1, 3, 127, 123456789,
                          std::numeric_limits<int32_t>::min(),
                          std::numeric_limits<int32_t>::max()};
  for (int32_t value : cases) {
    if (!Check(value)) {
      std::fprintf(stderr, "FAIL Perfetto enum wire value %d\n", value);
      return 1;
    }
  }
  std::puts("PASS 18 actual Perfetto enum serializer and validator checks");
  return 0;
}
