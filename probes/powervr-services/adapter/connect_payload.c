/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#include "connect_payload.h"

static uint32_t
read32(const unsigned char *p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
	    ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void
write32(unsigned char *p, uint32_t value)
{
	p[0] = (unsigned char)value;
	p[1] = (unsigned char)(value >> 8);
	p[2] = (unsigned char)(value >> 16);
	p[3] = (unsigned char)(value >> 24);
}

enum pvr_abi_connect_result
pvr_abi_connect_read_candidate(const void *bytes, size_t length,
    struct pvr_abi_connect_input *out)
{
	const unsigned char *p = bytes;
	struct pvr_abi_connect_input decoded;

	if (bytes == NULL || out == NULL || length != PVR_ABI_CONNECT_INPUT_BYTES)
		return PVR_ABI_CONNECT_INVALID;
	decoded.flags = read32(p);
	decoded.build_options = read32(p + 4);
	decoded.ddk_version = read32(p + 8);
	decoded.ddk_build = read32(p + 12);
	if (decoded.ddk_version != UINT32_C(0x0001000b))
		return PVR_ABI_CONNECT_VERSION_MISMATCH;
	if (decoded.ddk_build != UINT32_C(5516664))
		return PVR_ABI_CONNECT_BUILD_MISMATCH;
	*out = decoded;
	return PVR_ABI_CONNECT_OK;
}

enum pvr_abi_connect_result
pvr_abi_connect_write_reply(const struct pvr_abi_connect_output *reply,
    void *bytes, size_t length)
{
	struct pvr_abi_connect_output values;
	unsigned char *p = bytes;

	if (reply == NULL || bytes == NULL || length != PVR_ABI_CONNECT_OUTPUT_BYTES)
		return PVR_ABI_CONNECT_INVALID;
	values = *reply;
	p[0] = values.kernel_arch;
	write32(p + 1, values.capability_flags);
	write32(p + 5, values.pvr_bridges);
	write32(p + 9, values.rgx_bridges);
	write32(p + 13, values.ddk_error);
	return PVR_ABI_CONNECT_OK;
}
