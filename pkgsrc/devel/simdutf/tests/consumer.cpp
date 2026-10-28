#include <simdutf.h>
#include <cstring>
int main() {
  const char valid[] = "hello \xE2\x82\xAC";
  const char invalid[] = {char(0xC0), char(0xAF)};
  if (!simdutf::validate_utf8(valid, std::strlen(valid))) return 1;
  if (simdutf::validate_utf8(invalid, sizeof(invalid))) return 2;
  char16_t result[16] = {};
  if (simdutf::convert_utf8_to_utf16(valid, std::strlen(valid), result) != 7 || result[6] != 0x20ac) return 3;
  if (simdutf::base64_length_from_binary_with_lines(6, simdutf::base64_default, 4) != 9) return 4;
  return 0;
}
