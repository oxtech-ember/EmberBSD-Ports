/* Origin: EmberBSD (AI-assisted), MIT. */
#define STB_IMAGE_STATIC
#define STB_IMAGE_IMPLEMENTATION
#include <stb/stb_image.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { const unsigned char *data; int size, pos; } Input;
static int read_input(void *user, char *data, int size) {
    Input *in = (Input *)user;
    if (size > in->size - in->pos) size = in->size - in->pos;
    memcpy(data, in->data + in->pos, (size_t)size);
    in->pos += size;
    return size;
}
static void skip_input(void *user, int count) { ((Input *)user)->pos += count; }
static int eof_input(void *user) { Input *in = (Input *)user; return in->pos >= in->size; }

static const unsigned char gif[] = {
    0x47,0x49,0x46,0x38,0x39,0x61,1,0,1,0,0x80,0,0,
    0,0,0,0xff,0xff,0xff,0x21,0xf9,4,1,0,0,0,0,
    0x2c,0,0,0,0,1,0,1,0,0,2,1,0x44,0,0x3b
};

int main(int argc, char **argv)
{
    FILE *f;
    long size;
    int x, y, channels, frames, *delays = NULL;
    unsigned char *buf, *image;
    static const unsigned char hdr[] = "#?RADIANCE\n";
    Input hdr_input = { hdr, sizeof(hdr) - 1, 0 };
    stbi_io_callbacks callbacks = { read_input, skip_input, eof_input };
    unsigned char pic[111] = { 0x53, 0x80, 0xf6, 0x34 };
    if (argc != 2 || !(f = fopen(argv[1], "rb"))) return 1;
    if (fseek(f, 0, SEEK_END) || (size = ftell(f)) <= 0 || fseek(f, 0, SEEK_SET)) { fclose(f); return 2; }
    buf = (unsigned char *)malloc((size_t)size);
    if (!buf || fread(buf, 1, (size_t)size, f) != (size_t)size) { free(buf); fclose(f); return 3; }
    fclose(f);
    image = stbi_load_from_memory(buf, (int)size, &x, &y, &channels, 0);
    if (!image || x != 32 || y != 32) { stbi_image_free(image); free(buf); return 4; }
    stbi_image_free(image);
    image = stbi_load_from_memory(buf, (int)size, &x, &y, &channels, 4);
    if (!image || x != 32 || y != 32) { stbi_image_free(image); free(buf); return 5; }
    stbi_image_free(image);
    if (stbi_load_from_memory(buf, (int)size, &x, &y, &channels, -1) ||
        stbi_load_from_memory(buf, (int)size, &x, &y, &channels, 5)) { free(buf); return 6; }
    free(buf);
    pic[88] = 'P'; pic[89] = 'I'; pic[90] = 'C'; pic[91] = 'T';
    pic[93] = 1; pic[95] = 1;
    pic[105] = 8; pic[107] = 0xe0;
    pic[108] = 0x12; pic[109] = 0x34; pic[110] = 0x56;
    image = stbi_load_from_memory(pic, sizeof(pic), &x, &y, &channels, 3);
    if (!image || x != 1 || y != 1 || image[0] != 0x12 || image[1] != 0x34 || image[2] != 0x56) {
        stbi_image_free(image);
        return 9;
    }
    stbi_image_free(image);
    image = stbi_load_gif_from_memory(gif, sizeof(gif), &delays, &x, &y, &frames, &channels, 0);
    if (!image || x != 1 || y != 1 || frames != 1) { stbi_image_free(image); stbi_image_free(delays); return 7; }
    stbi_image_free(image);
    stbi_image_free(delays);
    if (!stbi_is_hdr_from_callbacks(&callbacks, &hdr_input)) return 10;
    return 0;
}
