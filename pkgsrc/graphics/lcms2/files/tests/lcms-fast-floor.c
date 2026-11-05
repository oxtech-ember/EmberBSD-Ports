/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Exercise Little CMS's actual interpolation floor at a legal grid boundary. */
#include "lcms2_internal.h"
#include <stdio.h>

int
main(void)
{
    const double values[] = { 32767.25, 32768.25, 49151.5, 65534.75 };
    unsigned int i;
    for (i = 0; i < sizeof(values) / sizeof(values[0]); i++) {
        int actual = _cmsQuickFloor(values[i]);
        int expected = (int)floor(values[i]);
        if (actual != expected) {
            fprintf(stderr, "floor(%g): %d, expected %d\n", values[i], actual, expected);
            return 1;
        }
    }
    return 0;
}
