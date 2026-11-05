/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Exercise the library's actual 8-bit matrix-shaper saturation path. */
#include "cmsopt.c"
#include <limits.h>
#include <stdio.h>
#include <string.h>

int
main(void)
{
    MatShaper8Data data;
    cmsUInt16Number input[3] = { 128 * 257, 0, 0 }, output[3] = {0};
    memset(&data, 0, sizeof(data));
    data.Shaper1R[128] = INT_MAX;
    data.Mat[0][0] = 16384;
    data.Shaper2R[16384] = 65535;
    MatShaperEval16(input, output, &data);
    if (output[0] != 65535) {
        fprintf(stderr, "saturated matrix output %u, expected 65535\n", output[0]);
        return 1;
    }
    return 0;
}
