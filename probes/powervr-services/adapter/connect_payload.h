/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#ifndef PVR_CONNECT_PAYLOAD_H
#define PVR_CONNECT_PAYLOAD_H

#include <stddef.h>
#include <stdint.h>

#define PVR_ABI_CONNECT_GROUP UINT32_C(1)
#define PVR_ABI_CONNECT_FUNCTION UINT32_C(0)
#define PVR_ABI_CONNECT_INPUT_BYTES 16
#define PVR_ABI_CONNECT_OUTPUT_BYTES 17

/* Native values, never overlays for packed foreign bytes. */
struct pvr_abi_connect_input {
	uint32_t flags;
	uint32_t build_options;
	uint32_t ddk_version;
	uint32_t ddk_build;
};

struct pvr_abi_connect_output {
	uint8_t kernel_arch;
	uint32_t capability_flags;
	uint32_t pvr_bridges;
	uint32_t rgx_bridges;
	uint32_t ddk_error;
};

enum pvr_abi_connect_result {
	PVR_ABI_CONNECT_OK,
	PVR_ABI_CONNECT_INVALID,
	PVR_ABI_CONNECT_VERSION_MISMATCH,
	PVR_ABI_CONNECT_BUILD_MISMATCH
};

/*
 * Require exact length and candidate 1.11@5516664 identity, little-endian.
 * Preserve *out on rejection. Flags/options remain unvalidated raw values.
 */
enum pvr_abi_connect_result pvr_abi_connect_read_candidate(const void *, size_t,
    struct pvr_abi_connect_input *);

/* Encode supplied values into exactly 17 bytes; preserve bytes on rejection. */
enum pvr_abi_connect_result pvr_abi_connect_write_reply(
    const struct pvr_abi_connect_output *, void *, size_t);

#endif /* PVR_CONNECT_PAYLOAD_H */
