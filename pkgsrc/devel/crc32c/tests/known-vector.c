#include <stdint.h>
#include <stdio.h>
#include <crc32c/crc32c.h>

int main(void)
{
    static const uint8_t data[] = "123456789";
    uint32_t value = crc32c_value(data, sizeof(data) - 1);
    if (value != UINT32_C(0xe3069283)) {
        fprintf(stderr, "CRC-32C mismatch: %08x\n", (unsigned)value);
        return 1;
    }
    return 0;
}
