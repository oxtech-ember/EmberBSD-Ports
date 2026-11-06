#include "buffer.h"
#include <cstdint>
#include <limits>
int main() {
  uint8_t data[4] = {1, 2, 3, 4};
  woff2::Buffer buf(data, sizeof(data));
  if (buf.set_offset(std::numeric_limits<size_t>::max())) return 1;
  if (buf.offset() != 0 || !buf.set_offset(3)) return 2;
  uint16_t value = 0;
  if (buf.ReadU16(&value) || buf.offset() != 3) return 3;
  if (!buf.set_offset(2) || !buf.ReadU16(&value) || value != 0x0304) return 4;
  return 0;
}
