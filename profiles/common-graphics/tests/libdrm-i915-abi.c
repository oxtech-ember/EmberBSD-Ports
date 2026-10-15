/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Fixed imported uAPI layout expectations. */
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <i915_drm.h>

#define CHECK_LAYOUT(type, bytes, engines_offset) \
    _Static_assert(sizeof(struct type) == bytes, #type " size"); \
    _Static_assert(_Alignof(struct type) == 1, #type " alignment"); \
    _Static_assert(offsetof(struct type, engines) == engines_offset, \
        #type " flexible-array offset")

CHECK_LAYOUT(i915_context_engines_load_balance, 48, 48);
CHECK_LAYOUT(i915_context_engines_bond, 80, 80);
CHECK_LAYOUT(i915_context_engines_parallel_submit, 72, 72);
CHECK_LAYOUT(i915_context_param_engines, 8, 8);
_Static_assert(offsetof(struct i915_context_engines_load_balance, flags) == 36,
    "load-balance flags offset");
_Static_assert(offsetof(struct i915_context_engines_bond, flags) == 40,
    "bond flags offset");
_Static_assert(offsetof(struct i915_context_engines_parallel_submit, flags) == 40,
    "parallel flags offset");

int
main(void)
{
    unsigned char storage[1 + sizeof(struct i915_context_engines_load_balance)
        + 2 * sizeof(struct i915_engine_class_instance)];
    struct i915_context_engines_load_balance *record;
    uint16_t index = 0x1234;
    uint64_t reserved = UINT64_C(0x123456789abcdef0);

    memset(storage, 0, sizeof(storage));
    record = (void *)(storage + 1);
    record->engine_index = index;
    record->mbz64 = reserved;
    if (memcmp(storage + 1 + 32, &index, sizeof(index)) != 0)
        return 1;
    if (memcmp(storage + 1 + 40, &reserved, sizeof(reserved)) != 0)
        return 2;
    return 0;
}
