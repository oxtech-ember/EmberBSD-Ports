/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#ifndef PVR_ERRNO_ABI_H
#define PVR_ERRNO_ABI_H

#if defined(__GNUC__)
#define PVR_ABI_PUBLIC __attribute__((visibility("default")))
#else
#define PVR_ABI_PUBLIC
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* Foreign Linux errno storage. This never returns the native errno slot. */
PVR_ABI_PUBLIC int *pvr_abi_errno_location(void);

/* Return the Linux errno number, or -1. Do not change either errno slot. */
PVR_ABI_PUBLIC int pvr_abi_errno_from_native(int);

/* Store a translated error. On unsupported input, return -1 and keep state. */
PVR_ABI_PUBLIC int pvr_abi_errno_set_native(int);

#ifdef __cplusplus
}
#endif

#undef PVR_ABI_PUBLIC
#endif
