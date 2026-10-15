// SPDX-License-Identifier: MIT
#include <onnxruntime_c_api.h>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <type_traits>

using Reason = OrtDeviceEpIncompatibilityReason;
struct Container { char prefix; Reason reason; };
static_assert(std::is_same_v<std::underlying_type_t<Reason>, int>);
static_assert(std::is_signed_v<std::underlying_type_t<Reason>>);
static_assert(sizeof(Reason) == 4 && alignof(Reason) == alignof(int));
static_assert(sizeof(Container) == 8 && offsetof(Container, reason) == 4);
static_assert(static_cast<int64_t>(OrtDeviceEpIncompatibility_UNKNOWN) == INT64_C(-2147483648));
static_assert(static_cast<uint32_t>(OrtDeviceEpIncompatibility_UNKNOWN) == UINT32_C(0x80000000));
static_assert(OrtDeviceEpIncompatibility_NONE == 0 && OrtDeviceEpIncompatibility_DRIVER_INCOMPATIBLE == 1 &&
    OrtDeviceEpIncompatibility_DEVICE_INCOMPATIBLE == 2 && OrtDeviceEpIncompatibility_MISSING_DEPENDENCY == 4);

int main()
{
    const Reason reason = OrtDeviceEpIncompatibility_UNKNOWN;
    std::printf("PASS C++ reason: value=%d enum=%zu alignment=%zu container=%zu mask=%08x\n",
        static_cast<int>(reason), sizeof(Reason), alignof(Reason), sizeof(Container),
        static_cast<unsigned>(static_cast<uint32_t>(reason)));
    return 0;
}
