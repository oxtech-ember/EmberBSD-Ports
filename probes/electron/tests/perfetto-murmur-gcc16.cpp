// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted E12 regression).

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>

#include "perfetto/ext/base/murmur_hash.h"

int main() {
  constexpr std::array<uint8_t, 16> kInput = {
      0x80, 0x91, 0xa2, 0xb3, 0xc4, 0xd5, 0xe6, 0xf7,
      0x08, 0x19, 0x2a, 0x3b, 0x4c, 0x5d, 0x6e, 0x7f};
  constexpr std::array<uint64_t, 16> kExpected = {
      0x9bfae0a4e613fc3cULL, 0x4a91221142e39cc2ULL,
      0x0497842417129c9eULL, 0x40ad0d4ff0c77facULL,
      0xee1d8af3bfcdcf4cULL, 0x8d14178225f12d8eULL,
      0xfc857149e7174e5bULL, 0xdcfdf75223a5797fULL,
      0x9e2207de5428df92ULL, 0xfdd3b9e0c65c3701ULL,
      0xf65c1f3e9aae2a93ULL, 0xd073f482e975fb9cULL,
      0x3daf95e07c80c4c0ULL, 0x7ef4cbc587621854ULL,
      0x78cda0a4a04cfdacULL, 0xbdc811b7012c849aULL};

  for (size_t length = 0; length < kInput.size(); ++length) {
    const uint64_t actual =
        perfetto::base::murmur_internal::MurmurHashBytes(kInput.data(), length);
    if (actual != kExpected[length]) {
      std::fprintf(stderr, "length %zu: got %016llx, expected %016llx\n",
                   length, static_cast<unsigned long long>(actual),
                   static_cast<unsigned long long>(kExpected[length]));
      return 1;
    }
  }
  return 0;
}
