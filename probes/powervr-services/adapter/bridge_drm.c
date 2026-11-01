/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#include "bridge_drm.h"

static uint32_t
get32(const unsigned char *p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
	    ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint64_t
get64(const unsigned char *p)
{
	return (uint64_t)get32(p) | ((uint64_t)get32(p + 4) << 32);
}

enum pvr_abi_bridge_result
pvr_abi_bridge_drm_decode(uint64_t request, const void *bytes, size_t length,
    struct pvr_abi_bridge_command *out)
{
	struct pvr_abi_bridge_command decoded;
	const unsigned char *p = bytes;

	if (request != PVR_ABI_DRM_REQUEST)
		return PVR_ABI_BRIDGE_UNSUPPORTED;
	if (bytes == NULL || out == NULL || length != PVR_ABI_DRM_BYTES)
		return PVR_ABI_BRIDGE_INVALID;
	decoded.bridge_id = get32(p);
	decoded.function_id = get32(p + 4);
	decoded.input_address = get64(p + 8);
	decoded.output_address = get64(p + 16);
	decoded.input_size = get32(p + 24);
	decoded.output_size = get32(p + 28);
	*out = decoded;
	return PVR_ABI_BRIDGE_OK;
}
