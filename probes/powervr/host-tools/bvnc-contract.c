/* SPDX-License-Identifier: MIT */
/* Test the extracted production parser and the actual device table. */
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pvr_device_info.h"
#include "bvnc-parser.inc"
static unsigned checks;
#define CHECK(c) do { ++checks; if (!(c)) { fprintf(stderr, "%s:%u: %s\n", __FILE__, __LINE__, #c); abort(); } } while (0)
static void valid(const char *s, uint64_t want) {
   uint64_t value = UINT64_C(0xfacefeeddeadbeef);
   CHECK(parse_bvnc(s, &value));
   CHECK(value == want);
}
static void invalid(const char *s) {
   uint64_t value = UINT64_C(0xfacefeeddeadbeef);
   CHECK(!parse_bvnc(s, &value));
   CHECK(value == UINT64_C(0xfacefeeddeadbeef));
}
int main(void) {
   char text[160];
   const char *bad[] = { "", "1", "1.2", "1.2.3", "1.2.3.", ".1.2.3", "1..2.3", "1.2..3", "-1.2.3.4", "+1.2.3.4", " 1.2.3.4", "1.2.3.4 ", "1.2.3.4x", "1.2.3.4.5", "65536.2.3.4", "1.65536.3.4", "1.2.65536.4", "1.2.3.65536", "4294967296.2.3.4", "1.2.3.9999999999999999999999999999999999999999999999999", "1.2.3.0x1", "1.2.3.4\n" };
   for (unsigned i = 0; i < ARRAY_SIZE(bad); ++i) invalid(bad[i]);
   valid("0.0.0.0", 0);
   valid("65535.65535.65535.65535", UINT64_MAX);
   valid("00036.00056.00104.00183", UINT64_C(0x00240038006800b7));
   for (unsigned field = 0; field < 4; ++field) {
      for (unsigned n = 0; n <= UINT16_MAX; ++n) {
         unsigned v[4] = { 36, 56, 104, 183 };
         v[field] = n;
         snprintf(text, sizeof(text), "%u.%u.%u.%u", v[0], v[1], v[2], v[3]);
         uint64_t want = ((uint64_t)v[0] << 48) | ((uint64_t)v[1] << 32) | ((uint64_t)v[2] << 16) | v[3];
         valid(text, want);
      }
   }
   /* Original public-name alias must retain its original first-match BVNC. */
   struct pvr_device_info named, exact;
   CHECK(pvr_device_info_init_public_name(&named, "BXM-4-64"));
   CHECK(pvr_get_packed_bvnc(&named) == UINT64_C(0x00240034006800b6));
   CHECK(pvr_device_info_is_supported(UINT64_C(0x00240038006800b7)));
   CHECK(pvr_device_info_init(&exact, UINT64_C(0x00240038006800b7)) == 0);
   CHECK(pvr_get_packed_bvnc(&exact) == UINT64_C(0x00240038006800b7));
   CHECK(!pvr_device_info_is_supported(0));
   CHECK(!pvr_device_info_is_supported(UINT64_MAX));
   CHECK(!pvr_device_info_is_supported(UINT64_C(0x00240038006800b8)));
   CHECK(!pvr_device_info_init_public_name(&exact, "not-a-device"));
   printf("PASS %u checks: actual BVNC parser and device table\n", checks);
   return 0;
}
