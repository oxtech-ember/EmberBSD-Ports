/* SPDX-License-Identifier: MIT */
#include <onnxruntime_c_api.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

typedef OrtDeviceEpIncompatibilityReason Reason;
struct Container { char prefix; Reason reason; };
_Static_assert(sizeof(Reason) == 4, "enum width changed");
_Static_assert(_Generic((Reason)0, int: 1, default: 0), "enum compatible type changed");
_Static_assert(sizeof(struct Container) == 8 && offsetof(struct Container, reason) == 4, "enum layout changed");
_Static_assert(OrtDeviceEpIncompatibility_UNKNOWN == (-2147483647 - 1), "signed value changed");
_Static_assert((uint32_t)OrtDeviceEpIncompatibility_UNKNOWN == UINT32_C(0x80000000), "mask changed");
_Static_assert(OrtDeviceEpIncompatibility_NONE == 0 && OrtDeviceEpIncompatibility_DRIVER_INCOMPATIBLE == 1 &&
    OrtDeviceEpIncompatibility_DEVICE_INCOMPATIBLE == 2 && OrtDeviceEpIncompatibility_MISSING_DEPENDENCY == 4,
    "other flags changed");

int main(void)
{
    const Reason reason = OrtDeviceEpIncompatibility_UNKNOWN;
    const uint32_t mask = (uint32_t)reason;
    printf("PASS C reason: value=%d enum=%zu container=%zu mask=%08x\n", (int)reason,
        sizeof(reason), sizeof(struct Container), (unsigned)mask);
    return 0;
}
