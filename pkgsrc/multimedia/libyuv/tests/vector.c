#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <libyuv/convert_argb.h>
#include <libyuv/convert_from_argb.h>
#include <libyuv/cpu_id.h>
#include <libyuv/rotate.h>

enum { W = 32, H = 16, Y = W * H, UV = W * H / 4 };
struct output { uint8_t argb[4*Y], y[Y], u[UV], v[UV], ry[Y], ru[UV], rv[UV]; };
static int run(struct output *out, int mask)
{
    uint8_t y[Y], u[UV], v[UV];
    int i;
    for (i = 0; i < Y; ++i) y[i] = (uint8_t)(16 + (i * 37) % 220);
    y[0] = 16; y[1] = 235;
    memset(u, 128, sizeof(u)); memset(v, 128, sizeof(v));
    MaskCpuFlags(mask);
    if (I420ToARGB(y,W,u,W/2,v,W/2,out->argb,W*4,W,H)) return 1;
    if (ARGBToI420(out->argb,W*4,out->y,W,out->u,W/2,out->v,W/2,W,H)) return 1;
    if (I420Rotate(out->y,W,out->u,W/2,out->v,W/2,out->ry,H,out->ru,H/2,out->rv,H/2,W,H,kRotate90)) return 1;
    return 0;
}
int main(void)
{
    struct output scalar, accelerated;
    if (run(&scalar, 1) || run(&accelerated, -1)) return 1;
    if (memcmp(&scalar, &accelerated, sizeof(scalar))) {
        fputs("scalar/SIMD mismatch\n", stderr); return 1;
    }
    if (scalar.argb[0] != 0 || scalar.argb[1] != 0 || scalar.argb[2] != 0 || scalar.argb[3] != 255 ||
        scalar.argb[4] != 255 || scalar.argb[5] != 255 || scalar.argb[6] != 255 || scalar.argb[7] != 255) {
        fputs("black/white known vector mismatch\n", stderr); return 1;
    }
    return 0;
}
