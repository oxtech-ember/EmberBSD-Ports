#include <simdutf.h>
#include <cstring>
#ifndef SIMDUTF_ATOMIC_REF
#error "C++20 atomic base64 API is unavailable"
#endif
int main() {
  char encoded[8] = {};
  if (simdutf::atomic_binary_to_base64("abc", 3, encoded) != 4 ||
      std::memcmp(encoded, "YWJj", 4) != 0) return 1;
  char decoded[8] = {};
  size_t size = sizeof(decoded);
  auto r = simdutf::atomic_base64_to_binary_safe(encoded, 4, decoded, size);
  if (r.error != simdutf::SUCCESS || size != 3 || std::memcmp(decoded, "abc", 3)) return 2;
  const char16_t wide[] = u"YWJj";
  size = sizeof(decoded);
  r = simdutf::atomic_base64_to_binary_safe(wide, 4, decoded, size);
  if (r.error != simdutf::SUCCESS || size != 3 || std::memcmp(decoded, "abc", 3)) return 3;
  size = sizeof(decoded);
  r = simdutf::atomic_base64_to_binary_safe("!!!!", 4, decoded, size);
  if (r.error == simdutf::SUCCESS) return 4;
  return 0;
}
