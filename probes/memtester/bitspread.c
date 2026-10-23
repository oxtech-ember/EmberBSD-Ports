/* SPDX-License-Identifier: GPL-2.0-only */
/* Origin: EmberBSD, AI-assisted by OpenAI Codex (GPT-6). */
/* Exercise upstream tests.c; observe buffers at its progress boundary. */
#include <sys/types.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


static unsigned long volatile buffer_a[7], buffer_b[7];
static size_t words;
static unsigned int pass;
static int corrupt;

static const unsigned long long patterns[] = {
    0x0000000000000005ULL,
    0x000000000000000aULL,
    0x0000000000000014ULL,
    0x0000000000000028ULL,
    0x0000000000000050ULL,
    0x00000000000000a0ULL,
    0x0000000000000140ULL,
    0x0000000000000280ULL,
    0x0000000000000500ULL,
    0x0000000000000a00ULL,
    0x0000000000001400ULL,
    0x0000000000002800ULL,
    0x0000000000005000ULL,
    0x000000000000a000ULL,
    0x0000000000014000ULL,
    0x0000000000028000ULL,
    0x0000000000050000ULL,
    0x00000000000a0000ULL,
    0x0000000000140000ULL,
    0x0000000000280000ULL,
    0x0000000000500000ULL,
    0x0000000000a00000ULL,
    0x0000000001400000ULL,
    0x0000000002800000ULL,
    0x0000000005000000ULL,
    0x000000000a000000ULL,
    0x0000000014000000ULL,
    0x0000000028000000ULL,
    0x0000000050000000ULL,
    0x00000000a0000000ULL,
    0x0000000140000000ULL,
    0x0000000280000000ULL,
    0x0000000500000000ULL,
    0x0000000a00000000ULL,
    0x0000001400000000ULL,
    0x0000002800000000ULL,
    0x0000005000000000ULL,
    0x000000a000000000ULL,
    0x0000014000000000ULL,
    0x0000028000000000ULL,
    0x0000050000000000ULL,
    0x00000a0000000000ULL,
    0x0000140000000000ULL,
    0x0000280000000000ULL,
    0x0000500000000000ULL,
    0x0000a00000000000ULL,
    0x0001400000000000ULL,
    0x0002800000000000ULL,
    0x0005000000000000ULL,
    0x000a000000000000ULL,
    0x0014000000000000ULL,
    0x0028000000000000ULL,
    0x0050000000000000ULL,
    0x00a0000000000000ULL,
    0x0140000000000000ULL,
    0x0280000000000000ULL,
    0x0500000000000000ULL,
    0x0a00000000000000ULL,
    0x1400000000000000ULL,
    0x2800000000000000ULL,
    0x5000000000000000ULL,
    0xa000000000000000ULL,
};

static int
observe_printf(const char *format, ...)
{
    unsigned int pattern_index, limit = sizeof(unsigned long) * 8 - 2;
    size_t i;
    unsigned long expected;

    if (strcmp(format, "testing %3u") != 0)
        return 0;
    if (pass >= 2 * limit) {
        fprintf(stderr, "FAIL: too many patterns at pass %u\n", pass);
        exit(1);
    }
    pattern_index = pass < limit ? pass : 2 * limit - 1 - pass;
    if (pattern_index >= sizeof(patterns) / sizeof(patterns[0])) {
        fprintf(stderr, "FAIL: pattern table pattern_index %u\n", pattern_index);
        exit(1);
    }
    expected = (unsigned long)patterns[pattern_index];
    for (i = 0; i < words; i++) {
        unsigned long want = i % 2 == 0 ? expected : ~expected;
        if (buffer_a[i + 1] != want || buffer_b[i + 1] != want) {
            fprintf(stderr, "FAIL: pass %u word %lu: %lx/%lx want %lx\n",
                pass, (unsigned long)i, buffer_a[i + 1], buffer_b[i + 1], want);
            exit(1);
        }
    }
    if (buffer_a[0] != 0x1357UL || buffer_b[0] != 0x1357UL ||
        buffer_a[words + 1] != 0x2468UL || buffer_b[words + 1] != 0x2468UL) {
        fprintf(stderr, "FAIL: buffer boundary\n");
        exit(1);
    }
    pass++;
    if (corrupt && words != 0)
        buffer_b[1] ^= 1UL;
    return 0;
}

/* Keep the real generator and comparator; only silence and observe progress. */
#define printf observe_printf
#include "tests.c"
#undef printf

int use_phys;
off_t physaddrbase;

int
main(void)
{
    static const size_t counts[] = { 1, 2, 5, 0 };
    size_t c;
    int result;

    for (c = 0; c < sizeof(counts) / sizeof(counts[0]); c++) {
        words = counts[c];
        buffer_a[0] = buffer_b[0] = 0x1357UL;
        buffer_a[words + 1] = buffer_b[words + 1] = 0x2468UL;
        pass = 0;
        result = test_bitspread_comparison(buffer_a + 1, buffer_b + 1, words);
        if (result != 0 || pass != 2 * (sizeof(unsigned long) * 8 - 2)) {
            fprintf(stderr, "FAIL: result %d, pattern count %u\n", result, pass);
            return 1;
        }
    }
    /* The actual comparator must reject buffer_a mismatch and stop the walk. */
    words = 1;
    buffer_a[0] = buffer_b[0] = 0x1357UL;
    buffer_a[words + 1] = buffer_b[words + 1] = 0x2468UL;
    pass = 0;
    corrupt = 1;
    result = test_bitspread_comparison(buffer_a + 1, buffer_b + 1, words);
    if (result != -1 || pass != 1) {
        fprintf(stderr, "FAIL: comparison failure did not stop the walk\n");
        return 1;
    }
    fprintf(stderr, "PASS: %u-bit, four lengths, both directions, complements, guards, comparator failure\n", (unsigned int)(sizeof(unsigned long) * 8));
    return 0;
}
