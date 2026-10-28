// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include "compression_utils_portable.h"
#include <assert.h>
#include <string.h>

int main() {
  const unsigned char input[] = "V8 snapshot data: shared zlib compression";
  unsigned char compressed[256], restored[256];
  const zlib_internal::WrapperType wrappers[] = {
    zlib_internal::ZLIB, zlib_internal::GZIP, zlib_internal::ZRAW
  };
  for (auto wrapper : wrappers) {
    uLongf compressed_size = sizeof(compressed), restored_size = sizeof(restored);
    assert(zlib_internal::CompressHelper(wrapper, compressed, &compressed_size, input,
          sizeof(input), Z_DEFAULT_COMPRESSION, nullptr, nullptr) == Z_OK);
    assert(zlib_internal::UncompressHelper(wrapper, restored, &restored_size,
          compressed, compressed_size) == Z_OK);
    assert(restored_size == sizeof(input));
    assert(memcmp(input, restored, sizeof(input)) == 0);
  }
}
