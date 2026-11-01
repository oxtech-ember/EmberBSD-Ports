/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../adapter/bridge_drm.h"

static unsigned int checks, failures;

#define CHECK(e) do { \
	checks++; \
	if (!(e)) { \
		fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #e); \
		failures++; \
	} \
} while (0)

/* Independent bytes at the six offsets in the selected DDK pvr_drm.h. */
static const unsigned char golden[32] = {
	0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
	0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
	0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff, 0x10,
	0x21, 0x43, 0x65, 0x87, 0x09, 0xab, 0xcd, 0xef
};

static int
same(const struct pvr_abi_bridge_command *a,
    const struct pvr_abi_bridge_command *b)
{
	return a->bridge_id == b->bridge_id &&
	    a->function_id == b->function_id &&
	    a->input_address == b->input_address &&
	    a->output_address == b->output_address &&
	    a->input_size == b->input_size &&
	    a->output_size == b->output_size;
}

static void
rejected(uint64_t request, const void *bytes, size_t length,
    enum pvr_abi_bridge_result expected)
{
	const struct pvr_abi_bridge_command initial = {
		1, 2, UINT64_C(0x8000000000000003), 4, 5, 6
	};
	struct pvr_abi_bridge_command out = initial;

	errno = ERANGE;
	CHECK(pvr_abi_bridge_drm_decode(request, bytes, length, &out) == expected);
	CHECK(same(&out, &initial));
	CHECK(errno == ERANGE);
}

int
main(void)
{
	struct pvr_abi_bridge_command out = { 0 };
	_Alignas(uint64_t) unsigned char unaligned[33];
	unsigned char zero[32] = { 0 }, full[32];
	size_t i;

	errno = EDOM;
	CHECK(pvr_abi_bridge_drm_decode(UINT64_C(0xc0206440), golden,
	    sizeof(golden), &out) == PVR_ABI_BRIDGE_OK);
	CHECK(errno == EDOM);
	CHECK(out.bridge_id == UINT32_C(0x04030201));
	CHECK(out.function_id == UINT32_C(0x08070605));
	CHECK(out.input_address == UINT64_C(0x8877665544332211));
	CHECK(out.output_address == UINT64_C(0x10ffeeddccbbaa99));
	CHECK(out.input_size == UINT32_C(0x87654321));
	CHECK(out.output_size == UINT32_C(0xefcdab09));
	memcpy(unaligned + 1, golden, sizeof(golden));
	CHECK(pvr_abi_bridge_drm_decode(PVR_ABI_DRM_REQUEST, unaligned + 1,
	    sizeof(golden), &out) == PVR_ABI_BRIDGE_OK);
	CHECK(out.input_address == UINT64_C(0x8877665544332211));
	CHECK(pvr_abi_bridge_drm_decode(PVR_ABI_DRM_REQUEST, zero,
	    sizeof(zero), &out) == PVR_ABI_BRIDGE_OK);
	CHECK(out.bridge_id == 0 && out.function_id == 0 &&
	    out.input_address == 0 && out.output_address == 0 &&
	    out.input_size == 0 && out.output_size == 0);
	memset(full, 0xff, sizeof(full));
	CHECK(pvr_abi_bridge_drm_decode(PVR_ABI_DRM_REQUEST, full,
	    sizeof(full), &out) == PVR_ABI_BRIDGE_OK);
	CHECK(out.bridge_id == UINT32_MAX && out.function_id == UINT32_MAX &&
	    out.input_address == UINT64_MAX && out.output_address == UINT64_MAX &&
	    out.input_size == UINT32_MAX && out.output_size == UINT32_MAX);
	for (i = 0; i < sizeof(golden); i++)
		rejected(PVR_ABI_DRM_REQUEST, golden, i, PVR_ABI_BRIDGE_INVALID);
	rejected(PVR_ABI_DRM_REQUEST, unaligned, sizeof(unaligned),
	    PVR_ABI_BRIDGE_INVALID);
	/* Length is rejected before any payload read. */
	rejected(PVR_ABI_DRM_REQUEST, golden, SIZE_MAX, PVR_ABI_BRIDGE_INVALID);
	rejected(PVR_ABI_DRM_REQUEST, NULL, sizeof(golden),
	    PVR_ABI_BRIDGE_INVALID);
	CHECK(pvr_abi_bridge_drm_decode(PVR_ABI_DRM_REQUEST, golden,
	    sizeof(golden), NULL) == PVR_ABI_BRIDGE_INVALID);
	/* Every request bit matters, including bits above the Linux u32 word. */
	for (i = 0; i < 64; i++)
		rejected(UINT64_C(0xc0206440) ^ (UINT64_C(1) << i), golden,
		    sizeof(golden), PVR_ABI_BRIDGE_UNSUPPORTED);
	printf("BRIDGE-DRM checks=%u failures=%u\n", checks, failures);
	return failures == 0 ? 0 : 65;
}
