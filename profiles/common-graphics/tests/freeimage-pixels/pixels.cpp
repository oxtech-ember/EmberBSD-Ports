// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), exact upstream AssignPixel storage contract.
#include "FreeImage.h"
#include "assign-pixel.hpp"
#include <cstdio>
#include <cstring>

int main() {
    const unsigned widths[] = {1, 2, 3, 4, 6, 8, 12, 16};
    for (unsigned width : widths) {
        for (unsigned offset = 1; offset != 5; ++offset) {
            alignas(16) BYTE source[32], target[32];
            for (unsigned i = 0; i != sizeof source; ++i)
                source[i] = static_cast<BYTE>(17 * i + 9);
            std::memset(target, 0xa5, sizeof target);
            AssignPixel(target + offset, source + offset, width);
            for (unsigned i = 0; i != sizeof target; ++i) {
                BYTE expected = (i >= offset && i < offset + width) ? source[i] : 0xa5;
                if (target[i] != expected) return 1;
            }
        }
    }
    std::puts("PASS: all eight pixel sizes, unaligned storage and exact guards.");
}
