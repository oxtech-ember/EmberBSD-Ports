/* Test actual internal decoder path with a controlled allocator failure. */
#include <stdlib.h>
#include <string.h>
#define OPJ_SKIP_POISON
#define opj_malloc test_malloc
#define opj_tcd_create test_tcd_create
#include "j2k.c"
#undef opj_malloc
#undef opj_tcd_create
static int calls, fail_at;
void *test_malloc(size_t n) { return ++calls == fail_at ? NULL : malloc(n); }
opj_tcd_t *test_tcd_create(OPJ_BOOL decoder) { (void)decoder; return NULL; }

static int run(int fail, int expect_mct, int expect_mcc)
{
    opj_j2k_t j = {0}; opj_stream_private_t stream = {0}; opj_event_mgr_t event = {0};
    opj_image_t image = {0}; opj_tcp_t tile = {0}, defaults = {0};
    opj_mct_data_t records[2] = {{0}};
    opj_simple_mcc_decorrelation_data_t mcc[1] = {{0}};
    opj_tccp_t default_tccp = {0};
    unsigned char data1 = 1, data2 = 2;
    records[0].m_data = &data1; records[0].m_data_size = 1;
    records[1].m_data = &data2; records[1].m_data_size = 1;
    mcc[0].m_decorrelation_array = &records[0];
    defaults.tccps = &default_tccp;
    defaults.m_mct_records = records; defaults.m_nb_mct_records = 2; defaults.m_nb_max_mct_records = 2;
    defaults.m_mcc_records = mcc; defaults.m_nb_mcc_records = 1; defaults.m_nb_max_mcc_records = 1;
    tile.tccps = calloc(1, sizeof(*tile.tccps));
    image.numcomps = 1; j.m_private_image = &image; j.m_cp.th = j.m_cp.tw = 1; j.m_cp.tcps = &tile;
    j.m_specific_param.m_decoder.m_default_tcp = &defaults;
    calls = 0; fail_at = fail;
    if (opj_j2k_copy_default_tcp_and_create_tcd(&j, &stream, &event) != OPJ_FALSE) return 1;
    if (tile.m_nb_mct_records != (OPJ_UINT32)expect_mct || tile.m_nb_mcc_records != (OPJ_UINT32)expect_mcc) return 2;
    if (expect_mct && tile.m_mct_records[0].m_data == records[0].m_data) return 3;
    if (expect_mcc && tile.m_mcc_records[0].m_decorrelation_array != &tile.m_mct_records[0]) return 4;
    opj_j2k_tcp_destroy(&tile);
    if (data1 != 1 || data2 != 2 || records[0].m_data != &data1 || records[1].m_data != &data2) return 5;
    return 0;
}
int main(void) { int a=run(3,1,0), b=run(1000,2,1); return a ? a : b; }
