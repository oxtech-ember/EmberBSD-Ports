/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Decode real IVF frames with the common libraries' own worker threads. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <dav1d/dav1d.h>
#include <aom/aom_decoder.h>
#include <aom/aomdx.h>
#include <vpx/vpx_decoder.h>
#include <vpx/vp8dx.h>

static unsigned char *
frame(const char *name, size_t *size)
{
    unsigned char header[32], fh[12], *data;
    FILE *f = fopen(name, "rb");
    if (!f || fread(header, 1, sizeof(header), f) != sizeof(header) ||
        memcmp(header, "DKIF", 4) || fread(fh, 1, sizeof(fh), f) != sizeof(fh))
        return NULL;
    *size = (size_t)fh[0] | (size_t)fh[1] << 8 | (size_t)fh[2] << 16 | (size_t)fh[3] << 24;
    if (!*size || *size > 16 * 1024 * 1024 || !(data = malloc(*size)))
        return NULL;
    if (fread(data, 1, *size, f) != *size) { free(data); data = NULL; }
    fclose(f);
    return data;
}

int main(int argc, char **argv)
{
    Dav1dSettings settings; Dav1dContext *decoder = NULL; Dav1dData packet = {0};
    Dav1dPicture picture = {0}; vpx_codec_ctx_t vpx; vpx_codec_dec_cfg_t cfg = {0};
    vpx_codec_iter_t iter = NULL; aom_codec_ctx_t aom;
    aom_codec_dec_cfg_t aom_cfg = {0}; aom_codec_iter_t aom_iter = NULL;
    unsigned char *data, *dst; size_t size;
    if (argc != 3 || !(data = frame(argv[1], &size))) return 1;
    dav1d_default_settings(&settings); settings.n_threads = 2; settings.max_frame_delay = 1;
    if (dav1d_open(&decoder, &settings) < 0 || !(dst = dav1d_data_create(&packet, size))) return 2;
    memcpy(dst, data, size); free(data);
    if (dav1d_send_data(decoder, &packet) < 0 || dav1d_get_picture(decoder, &picture) < 0) return 3;
    if (!picture.p.w || !picture.p.h) return 4;
    dav1d_picture_unref(&picture); dav1d_close(&decoder);
    if (!(data = frame(argv[1], &size))) return 5;
    aom_cfg.threads = 2;
    if (aom_codec_dec_init(&aom, aom_codec_av1_dx(), &aom_cfg, 0) ||
        aom_codec_decode(&aom, data, size, NULL) ||
        !aom_codec_get_frame(&aom, &aom_iter)) return 7;
    free(data);
    if (aom_codec_destroy(&aom) != AOM_CODEC_OK) return 8;
    if (!(data = frame(argv[2], &size))) return 5;
    cfg.threads = 2;
    if (vpx_codec_dec_init(&vpx, vpx_codec_vp9_dx(), &cfg, 0) ||
        vpx_codec_decode(&vpx, data, (unsigned int)size, NULL, 0) ||
        !vpx_codec_get_frame(&vpx, &iter)) return 6;
    free(data);
    return vpx_codec_destroy(&vpx) != VPX_CODEC_OK;
}
