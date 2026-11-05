#include <stdlib.h>
#include <string.h>
#define OPJ_SKIP_POISON
#define opj_malloc test_malloc
#include "image.c"
#undef opj_malloc
static int fail_at, calls;
void *test_malloc(size_t n) { return ++calls == fail_at ? NULL : malloc(n); }
int main(void)
{
    opj_image_t src = {0}, dest = {0};
    opj_image_comp_t comp = {0}; unsigned char profile[2] = {1, 2};
    if (opj_copy_image_header(&src, &dest) != OPJ_FALSE) return 1;
    src.numcomps = 1; src.comps = &comp; comp.w = 7; comp.h = 9;
    src.icc_profile_buf = profile; src.icc_profile_len = 2;
    fail_at = 1; calls = 0;
    if (opj_copy_image_header(&src, &dest) != OPJ_FALSE || dest.comps || dest.numcomps) return 2;
    fail_at = 2; calls = 0;
    if (opj_copy_image_header(&src, &dest) != OPJ_FALSE || !dest.comps || dest.icc_profile_buf || dest.icc_profile_len) return 3;
    opj_free(dest.comps); memset(&dest, 0, sizeof(dest));
    fail_at = 0; calls = 0;
    if (opj_copy_image_header(&src, &dest) != OPJ_TRUE || !dest.comps || dest.comps[0].w != 7 || dest.comps[0].h != 9 || !dest.icc_profile_buf || memcmp(dest.icc_profile_buf, profile, 2)) return 4;
    opj_free(dest.comps); opj_free(dest.icc_profile_buf);
    return 0;
}
