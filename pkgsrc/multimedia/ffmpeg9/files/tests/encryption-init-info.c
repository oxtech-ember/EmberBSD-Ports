/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <assert.h>
#include <stdint.h>
#include <limits.h>
#include <stdlib.h>
#include <libavutil/encryption_info.h>
#include <libavutil/mem.h>

int main(void)
{
    AVEncryptionInitInfo *list = NULL, *entry, *decoded;
    uint8_t *side = NULL;
    size_t size = 0;
    unsigned int allocated = 0, growth = 0, last = 0;
    for (int i = 0; i < 100000; ++i) {
        entry = av_encryption_init_info_alloc(16, 0, 0, 0);
        assert(entry);
        entry->next = list;
        list = entry;
    }
    av_encryption_init_info_free(list);
    entry = av_encryption_init_info_alloc(16, 0, 0, 0);
    assert(entry);
    for (int i = 0; i < 10000; ++i) {
        assert(av_encryption_init_info_append_side_data(&side, &size, &allocated, entry) == 0);
        if (allocated != last) { ++growth; last = allocated; }
    }
    assert(growth < 200);
    uint8_t *saved_side = side;
    size_t saved_size = size;
    allocated = 0; /* Force the next append to request allocation. */
    av_max_alloc(1);
    assert(av_encryption_init_info_append_side_data(&side, &size, &allocated, entry) < 0);
    assert(side == saved_side && size == saved_size);
    av_max_alloc(INT_MAX);
    decoded = av_encryption_init_info_get_side_data(side, size);
    assert(decoded);
    int count = 0;
    for (AVEncryptionInitInfo *p = decoded; p; p = p->next) ++count;
    assert(count == 10000);
    av_encryption_init_info_free(decoded);
    av_encryption_init_info_free(entry);
    av_free(side);
    return 0;
}
