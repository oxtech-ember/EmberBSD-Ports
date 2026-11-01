/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#ifndef PVR_BRIDGE_DRM_H
#define PVR_BRIDGE_DRM_H

#include <stddef.h>
#include <stdint.h>

/* Linux AArch64 request and byte count, not a native BSD ioctl number. */
#define PVR_ABI_DRM_REQUEST UINT64_C(0xc0206440)
#define PVR_ABI_DRM_BYTES 32

/* Native values, not a structure to cast over foreign memory. */
struct pvr_abi_bridge_command {
	uint32_t bridge_id;
	uint32_t function_id;
	uint64_t input_address;
	uint64_t output_address;
	uint32_t input_size;
	uint32_t output_size;
};

enum pvr_abi_bridge_result {
	PVR_ABI_BRIDGE_OK,
	PVR_ABI_BRIDGE_UNSUPPORTED,
	PVR_ABI_BRIDGE_INVALID
};

/*
 * Decode one complete little-endian outer command. On failure keep *out.
 * bytes must reference length readable bytes; out must be writable.
 * Null arguments are invalid. Addresses remain opaque integers.
 * This does not validate payloads, authorize commands or perform an ioctl.
 */
enum pvr_abi_bridge_result pvr_abi_bridge_drm_decode(uint64_t,
    const void *, size_t, struct pvr_abi_bridge_command *);

#endif /* PVR_BRIDGE_DRM_H */
