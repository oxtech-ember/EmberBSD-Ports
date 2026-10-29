// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <simdjson.h>
#include <simdutf.h>
#include <cstdint>
int main() {
  simdjson::dom::parser parser;
  std::uint64_t value = 0;
  simdjson::padded_string data("{\"value\":42}", 12);
  auto object = parser.parse(data);
  if (object["value"].get(value) || value != 42) return 1;
  return simdutf::validate_utf8("hello", 5) ? 0 : 2;
}
