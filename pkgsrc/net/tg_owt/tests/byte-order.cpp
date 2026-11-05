#include "rtc_base/byte_order.h"
#include <cstdint>
#include <cstring>

int main() {
  uint8_t b[8]{};
  const uint8_t be16[] = {0x12, 0x34}, le16[] = {0x34, 0x12};
  const uint8_t be32[] = {0x12, 0x34, 0x56, 0x78}, le32[] = {0x78, 0x56, 0x34, 0x12};
  const uint8_t be64[] = {0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef};
  const uint8_t le64[] = {0xef, 0xcd, 0xab, 0x89, 0x67, 0x45, 0x23, 0x01};
  rtc::SetBE16(b, 0x1234); if (std::memcmp(b, be16, 2) || rtc::GetBE16(be16) != 0x1234) return 1;
  rtc::SetLE16(b, 0x1234); if (std::memcmp(b, le16, 2) || rtc::GetLE16(le16) != 0x1234) return 2;
  rtc::SetBE32(b, 0x12345678); if (std::memcmp(b, be32, 4) || rtc::GetBE32(be32) != 0x12345678) return 3;
  rtc::SetLE32(b, 0x12345678); if (std::memcmp(b, le32, 4) || rtc::GetLE32(le32) != 0x12345678) return 4;
  rtc::SetBE64(b, UINT64_C(0x0123456789abcdef)); if (std::memcmp(b, be64, 8) || rtc::GetBE64(be64) != UINT64_C(0x0123456789abcdef)) return 5;
  rtc::SetLE64(b, UINT64_C(0x0123456789abcdef)); if (std::memcmp(b, le64, 8) || rtc::GetLE64(le64) != UINT64_C(0x0123456789abcdef)) return 6;
}
