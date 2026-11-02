/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#ifndef PVR_SERVICES_IOCTL_H
#define PVR_SERVICES_IOCTL_H

#include <stddef.h>
#include <stdint.h>

struct pvr_abi_services_command {
	uint32_t bridge_id;
	uint32_t function_id;
	uint32_t input_size;
	uint32_t output_size;
	/* Zero or a positive native transport errno; not PVRSRV_ERROR. */
	int (*invoke)(void *, const void *, void *);
};

struct pvr_abi_services {
	/* Trusted configuration and one live, caller-owned connection. */
	void *connection;
	const struct pvr_abi_services_command *commands;
	size_t command_count;
	void *memory_cookie;
	/* Checked foreign-memory copies: zero or a native transport errno. */
	int (*read_memory)(void *, uint64_t, void *, size_t);
	int (*write_memory)(void *, uint64_t, const void *, size_t);
	/* Disjoint writable scratch buffers, private to this call. */
	void *input;
	size_t input_capacity;
	void *output;
	size_t output_capacity;
};

/*
 * Typed core, not a variadic ioctl symbol replacement. argument is an opaque
 * foreign address. request is a zero-extended Linux u32. All callbacks and
 * configuration must remain valid and unchanged during the call.
 * Return zero or -1 with foreign TLS errno; preserve native errno.
 * This supplies no real device handler, memory backend or fd registry.
 */
int pvr_abi_services_ioctl(const struct pvr_abi_services *, uint64_t, uint64_t);

#endif /* PVR_SERVICES_IOCTL_H */
