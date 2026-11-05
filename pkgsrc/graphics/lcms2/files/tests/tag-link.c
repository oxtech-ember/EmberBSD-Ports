/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Preserve valid tone-curve links and reject a tone-curve-to-colorant link. */
#include <lcms2.h>
#include <stdlib.h>
#include <stdio.h>
int
main(void)
{
    cmsHPROFILE original = cmsCreate_sRGBProfile(), profile;
    cmsToneCurve *curve;
    cmsUInt32Number size = 0;
    unsigned char *data;
    if (!original)
        return 1;
    curve = cmsBuildGamma(NULL, 2.2);
    if (!curve || !cmsWriteTag(original, cmsSigGreenTRCTag, curve))
        return 1;
    cmsFreeToneCurve(curve);
    if (!cmsSaveProfileToMem(original, NULL, &size) || !size)
        return 1;
    data = malloc(size);
    if (!data || !cmsSaveProfileToMem(original, data, &size))
        return 2;
    profile = cmsOpenProfileFromMem(data, size);
    free(data);
    cmsCloseProfile(original);
    if (!profile)
        return 3;
    if (!cmsLinkTag(profile, cmsSigRedTRCTag, cmsSigGreenTRCTag) ||
        !cmsReadRawTag(profile, cmsSigRedTRCTag, NULL, 0))
        return 4;
    if (!cmsLinkTag(profile, cmsSigRedTRCTag, cmsSigRedColorantTag))
        return 5;
    if (cmsReadRawTag(profile, cmsSigRedTRCTag, NULL, 0)) {
        fputs("tone curve link exposed a colorant tag\n", stderr);
        return 6;
    }
    cmsCloseProfile(profile);
    return 0;
}
