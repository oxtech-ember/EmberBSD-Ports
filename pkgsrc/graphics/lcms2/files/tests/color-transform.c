/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Round-trip a normal sRGB profile and convert an RGB pixel. */
#include <lcms2.h>
#include <stdlib.h>
int
main(void)
{
    cmsHPROFILE original = cmsCreate_sRGBProfile(), source, target;
    cmsHTRANSFORM transform;
    cmsUInt32Number size = 0;
    unsigned char *serialized, in[3] = {255, 0, 0}, out[3] = {0};
    if (!original || !cmsSaveProfileToMem(original, NULL, &size) || !size)
        return 1;
    serialized = malloc(size);
    if (!serialized || !cmsSaveProfileToMem(original, serialized, &size))
        return 2;
    source = cmsOpenProfileFromMem(serialized, size);
    free(serialized);
    target = cmsCreate_sRGBProfile();
    if (!source || !target)
        return 3;
    transform = cmsCreateTransform(source, TYPE_RGB_8, target, TYPE_BGR_8,
                                   INTENT_PERCEPTUAL, 0);
    cmsCloseProfile(original);
    cmsCloseProfile(source);
    cmsCloseProfile(target);
    if (!transform)
        return 4;
    cmsDoTransform(transform, in, out, 1);
    cmsDeleteTransform(transform);
    return out[0] > 2 || out[1] > 2 || out[2] < 253;
}
