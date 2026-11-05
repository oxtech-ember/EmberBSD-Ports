/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <stdint.h>
#include <webp/decode.h>
#include <webp/demux.h>
#include <webp/encode.h>
#include <webp/mux.h>
#include <sharpyuv/sharpyuv.h>

int main(void) {
  const uint8_t pixel[4] = {255, 0, 0, 255};
  uint8_t *encoded = 0;
  const size_t size = WebPEncodeLosslessRGBA(pixel, 1, 1, 4, &encoded);
  int width = 0, height = 0;
  uint8_t *decoded = WebPDecodeRGBA(encoded, size, &width, &height);
  int ok = decoded && width == 1 && height == 1 && decoded[0] == 255 &&
           SharpYuvGetVersion() && WebPGetDemuxVersion() && WebPGetMuxVersion();
  WebPFree(decoded);
  WebPFree(encoded);
  return ok ? 0 : 1;
}
