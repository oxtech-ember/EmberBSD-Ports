// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <cstdint>
#include <initializer_list>
#include <limits>
#include <type_traits>

#include "services/network/public/mojom/host_resolver.mojom-shared-internal.h"

using Tristate = network::mojom::internal::DnsConfigOverrides_Tristate_Data;
using SecureMode = network::mojom::internal::OptionalSecureDnsMode_Data;
using Validator = bool (*)(int32_t, mojo::internal::ValidationContext*);
static_assert(!Tristate::kIsExtensible);
static_assert(!SecureMode::kIsExtensible);
static_assert(std::is_same_v<decltype(&Tristate::Validate), Validator>);
static_assert(std::is_same_v<decltype(&SecureMode::Validate), Validator>);

int main() {
  for (int32_t value : {0, 1, 2}) {
    if (!Tristate::IsKnownValue(value))
      return 1;
  }
  for (int32_t value : {0, 1, 2, 3}) {
    if (!SecureMode::IsKnownValue(value))
      return 2;
  }
  for (int32_t value : {-1, 3, std::numeric_limits<int32_t>::max()}) {
    if (Tristate::IsKnownValue(value))
      return 3;
  }
  for (int32_t value : {-1, 4, std::numeric_limits<int32_t>::max()}) {
    if (SecureMode::IsKnownValue(value))
      return 4;
  }
  return 0;
}
