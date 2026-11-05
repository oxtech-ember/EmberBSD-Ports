/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* A grid allocation must reject a wrapped product before allocating. */
#include <lcms2.h>
#include <stdio.h>
int
main(void)
{
    const cmsUInt32Number dimensions[] = {32768, 2};
    cmsStage *integer = cmsStageAllocCLut16bitGranular(NULL, dimensions, 2, 65537, NULL);
    cmsStage *floating = cmsStageAllocCLutFloatGranular(NULL, dimensions, 2, 65537, NULL);
    if (integer || floating) {
        if (integer) cmsStageFree(integer);
        if (floating) cmsStageFree(floating);
        fputs("wrapped grid allocation accepted\n", stderr);
        return 1;
    }
    return 0;
}
