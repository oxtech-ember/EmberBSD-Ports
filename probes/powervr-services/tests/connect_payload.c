/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../adapter/connect_payload.h"

static unsigned int checks, failures;

#define CHECK(e) do { \
	checks++; \
	if (!(e)) { \
		fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #e); \
		failures++; \
	} \
} while (0)

/* Literal input: flags/options, packed 1.11, build 5516664 (0x542d78). */
static const unsigned char candidate[16] = {
	0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
	0x0b, 0x00, 0x01, 0x00, 0x78, 0x2d, 0x54, 0x00
};

static void
reject_input(const void *bytes, size_t length, enum pvr_abi_connect_result want)
{
	struct pvr_abi_connect_input out = { 1, 2, 3, 4 };

	errno = EDOM;
	CHECK(pvr_abi_connect_read_candidate(bytes, length, &out) == want);
	CHECK(out.flags == 1 && out.build_options == 2 &&
	    out.ddk_version == 3 && out.ddk_build == 4);
	CHECK(errno == EDOM);
}

int
main(void)
{
	static const unsigned char golden_reply[17] = {
		64, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
		0x99, 0xaa, 0xbb, 0xcc, 0x26, 0x00, 0x00, 0x00
	};
	struct pvr_abi_connect_input out = { 0 };
	const struct pvr_abi_connect_output reply = {
		64, UINT32_C(0x44332211), UINT32_C(0x88776655),
		UINT32_C(0xccbbaa99), 38
	};
	_Alignas(uint64_t) unsigned char input[17], wire[19];
	unsigned char mutated[16];
	size_t i;

	errno = ERANGE;
	CHECK(pvr_abi_connect_read_candidate(candidate, sizeof(candidate),
	    &out) == PVR_ABI_CONNECT_OK);
	CHECK(out.flags == UINT32_C(0x44332211));
	CHECK(out.build_options == UINT32_C(0x88776655));
	CHECK(out.ddk_version == UINT32_C(0x0001000b));
	CHECK(out.ddk_build == UINT32_C(5516664));
	CHECK(errno == ERANGE);
	memcpy(input + 1, candidate, sizeof(candidate));
	CHECK(pvr_abi_connect_read_candidate(input + 1, sizeof(candidate),
	    &out) == PVR_ABI_CONNECT_OK);
	CHECK(out.flags == UINT32_C(0x44332211));
	/* A change in each version/build byte must reject candidate identity. */
	for (i = 8; i < 16; i++) {
		memcpy(mutated, candidate, sizeof(mutated));
		mutated[i] ^= 1;
		reject_input(mutated, sizeof(mutated), i < 12 ?
		    PVR_ABI_CONNECT_VERSION_MISMATCH : PVR_ABI_CONNECT_BUILD_MISMATCH);
	}
	for (i = 0; i < 16; i++)
		reject_input(candidate, i, PVR_ABI_CONNECT_INVALID);
	reject_input(input, sizeof(input), PVR_ABI_CONNECT_INVALID);
	reject_input(candidate, SIZE_MAX, PVR_ABI_CONNECT_INVALID);
	reject_input(NULL, sizeof(candidate), PVR_ABI_CONNECT_INVALID);
	CHECK(pvr_abi_connect_read_candidate(candidate, sizeof(candidate),
	    NULL) == PVR_ABI_CONNECT_INVALID);
	memset(wire, 0xa5, sizeof(wire));
	errno = ERANGE;
	CHECK(pvr_abi_connect_write_reply(&reply, wire + 1, 17) == PVR_ABI_CONNECT_OK);
	CHECK(memcmp(wire + 1, golden_reply, sizeof(golden_reply)) == 0);
	CHECK(wire[0] == 0xa5 && wire[18] == 0xa5);
	CHECK(errno == ERANGE);
	for (i = 0; i <= 18; i++) {
		if (i == 17)
			continue;
		memset(wire, 0xa5, sizeof(wire));
		CHECK(pvr_abi_connect_write_reply(&reply, wire, i) ==
		    PVR_ABI_CONNECT_INVALID);
		CHECK(wire[0] == 0xa5 && wire[16] == 0xa5 && wire[18] == 0xa5);
	}
	CHECK(pvr_abi_connect_write_reply(&reply, NULL, 17) == PVR_ABI_CONNECT_INVALID);
	CHECK(pvr_abi_connect_write_reply(NULL, wire, 17) == PVR_ABI_CONNECT_INVALID);
	CHECK(pvr_abi_connect_write_reply(&reply, wire, SIZE_MAX) == PVR_ABI_CONNECT_INVALID);
	printf("CONNECT-PAYLOAD checks=%u failures=%u\n", checks, failures);
	return failures == 0 ? 0 : 65;
}
