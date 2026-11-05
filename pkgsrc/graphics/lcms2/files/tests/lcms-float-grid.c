/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Evaluate a legal two-dimensional high-resolution interpolation grid. */
#include <lcms2.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

int
main(void)
{
    const cmsUInt32Number dimensions[] = {65536, 2};
    const cmsFloat32Number input[] = {0.75f, 0.5f};
    cmsFloat32Number *table = calloc(65536u * 2u, sizeof(*table));
    cmsFloat32Number output = -1;
    cmsPipeline *pipeline;
    cmsStage *stage;
    unsigned int x;
    if (!table)
        return 1;
    for (x = 0; x < 65536; x++)
        table[x * 2] = table[x * 2 + 1] = (float)x / 65535.0f;
    stage = cmsStageAllocCLutFloatGranular(NULL, dimensions, 2, 1, table);
    free(table);
    pipeline = cmsPipelineAlloc(NULL, 2, 1);
    if (!stage || !pipeline || !cmsPipelineInsertStage(pipeline, cmsAT_END, stage))
        return 2;
    cmsPipelineEvalFloat(input, &output, pipeline);
    cmsPipelineFree(pipeline);
    if (fabsf(output - 0.75f) > 0.0001f) {
        fprintf(stderr, "grid interpolation: %g, expected 0.75\n", output);
        return 3;
    }
    return 0;
}
