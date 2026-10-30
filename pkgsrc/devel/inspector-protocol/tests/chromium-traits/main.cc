// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include <cassert>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
#include "third_party/inspector_protocol/crdtp/chromium/protocol_traits.h"
#include "third_party/inspector_protocol/crdtp/cbor.h"

int main() {
  using namespace crdtp;
  const std::vector<uint16_t> units = {0x41, 0, 0x00e9, 0xd83d, 0xde00};
  std::vector<uint8_t> encoded;
  cbor::EncodeString16(span<uint16_t>(units.data(), units.size()), &encoded);
  const std::string expected("A\0\xc3\xa9\xf0\x9f\x98\x80", 8);
  bool saw_unaligned = false;
  for (size_t padding = 0; padding != 2; ++padding) {
    auto data = std::make_shared<std::vector<uint8_t>>(padding, 0);
    data->insert(data->end(), encoded.begin(), encoded.end());
    DeserializerState state(data, span<uint8_t>(data->data() + padding, encoded.size()));
    const auto bytes = state.tokenizer()->GetString16WireRep();
    saw_unaligned |= reinterpret_cast<uintptr_t>(bytes.data()) % 2 != 0;
    std::string value;
    assert(ProtocolTypeTraits<std::string>::Deserialize(&state, &value));
    assert(state.status().ok() && value == expected);
  }
  assert(saw_unaligned);
  std::vector<uint8_t> ascii;
  const std::string input("x\0y", 3);
  cbor::EncodeString8(span<uint8_t>(reinterpret_cast<const uint8_t*>(input.data()), input.size()), &ascii);
  DeserializerState ascii_state(std::move(ascii));
  std::string value;
  assert(ProtocolTypeTraits<std::string>::Deserialize(&ascii_state, &value) && value == input);
  std::vector<uint8_t> integer;
  cbor::EncodeInt32(123, &integer);
  DeserializerState wrong(std::move(integer));
  assert(!ProtocolTypeTraits<std::string>::Deserialize(&wrong, &value));
  assert(wrong.status().error == Error::BINDINGS_STRING_VALUE_EXPECTED);
}
