/* Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: MIT */
/* Include exact production functions between this fixture and TEST_MAIN. */
#ifndef TEST_MAIN
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cairo.h>
#include <lzo2a.h>
#include <zlib.h>
#define HAVE_LZO 1
#define HAVE_ZLIB 1
#define _csi_unlikely(x) (x)
#define _csi_error(x) (x)
#define CSI_STATUS_SUCCESS CAIRO_STATUS_SUCCESS
#define CSI_STATUS_READ_ERROR CAIRO_STATUS_READ_ERROR
#define CSI_OBJECT_TYPE_FILE 1
#define CSI_OBJECT_TYPE_STRING 2
#define BYTES 1
#define CSI_BITSWAP8_IF_LITTLE_ENDIAN(x) (x)
#define bswap_16(x) __builtin_bswap16(x)
#define bswap_32(x) __builtin_bswap32(x)
typedef cairo_status_t csi_status_t;
typedef struct { int type, ref; } csi_compound_object_t;
typedef struct { csi_compound_object_t base; long len, deflate;
    enum { NONE, ZLIB, LZO } method; char *string; } csi_string_t;
typedef struct { csi_compound_object_t base; int type; void *src;
    void *data; uint8_t *bp; int rem; } csi_file_t;
typedef struct { int type; union { csi_string_t *string; csi_file_t *file; } datum; } csi_object_t;
typedef struct { struct { void *closure; cairo_surface_t *(*create_source_image)
    (void *, cairo_format_t, int, int, long); } hooks; } csi_t;

/* Preserve generous red zones so the unpatched control has a deterministic
 * failed assertion instead of corrupting the process allocator. */
static unsigned char *allocation;
static size_t allocation_size;
static int invalid_allocation, slab_live, fail_string_allocation;
static void *guard_alloc(int size)
{
    if (size <= 0 || size > 4096) { invalid_allocation++; return NULL; }
    assert(allocation == NULL);
    allocation_size = (size_t)size;
    allocation = malloc(allocation_size + 512);
    assert(allocation);
    memset(allocation, 0xa5, allocation_size + 512);
    return allocation;
}
static int guard_valid(void)
{
    if (!allocation) return 1;
    for (size_t n = allocation_size; n < allocation_size + 512; n++)
        if (allocation[n] != 0xa5) return 0;
    return 1;
}
static void *_csi_alloc(csi_t *ctx, int size)
{ (void)ctx; return guard_alloc(size); }
static void _csi_free(csi_t *ctx, void *p)
{ (void)ctx; assert(p == allocation); /* Retain for guard inspection. */ }
static void *_csi_slab_alloc(csi_t *ctx, size_t n)
{ (void)ctx; void *p = calloc(1, n); if (p) slab_live++; return p; }
static void _csi_slab_free(csi_t *ctx, void *p, size_t n)
{ (void)ctx; (void)n; assert(p && slab_live > 0); slab_live--; free(p); }
static csi_status_t csi_string_new(csi_t *ctx, csi_object_t *obj,
    const char *str, int len)
{
    (void)ctx; assert(!str);
    if (fail_string_allocation) return CAIRO_STATUS_NO_MEMORY;
    if (len < 0 || len >= INT_MAX) { invalid_allocation++; return CSI_STATUS_READ_ERROR; }
    csi_string_t *s = calloc(1, sizeof(*s)); assert(s);
    s->string = guard_alloc(len + 1);
    if (!s->string) { free(s); return CAIRO_STATUS_NO_MEMORY; }
    s->len = len; obj->datum.string = s; return CSI_STATUS_SUCCESS;
}
static void csi_string_free(csi_t *ctx, csi_string_t *s)
{ (void)ctx; free(s); }
static csi_status_t csi_object_as_file(csi_t *ctx, csi_object_t *src, csi_object_t *file)
{ (void)ctx; (void)src; (void)file; abort(); }
static int csi_file_read(csi_file_t *file, void *buf, int size)
{ (void)file; (void)buf; (void)size; abort(); }
static void csi_object_free(csi_t *ctx, csi_object_t *file)
{ (void)ctx; (void)file; abort(); }
static cairo_surface_t *create_image(void *closure, cairo_format_t fmt,
    int width, int height, long unused)
{
    (void)closure; (void)unused;
    int stride = cairo_format_stride_for_width(fmt, width);
    unsigned char *p = guard_alloc(stride * height); assert(p);
    return cairo_image_surface_create_for_data(p, fmt, width, height, stride);
}
#else
int main(int argc, char **argv)
{
    assert(argc == 3);
    assert(lzo_init() == LZO_E_OK);
    unsigned char plain[64], compressed[1024];
    for (size_t i = 0; i < sizeof(plain); i++) plain[i] = (unsigned char)(i + 1);
    void *work = malloc(LZO2A_999_MEM_COMPRESS); assert(work);
    lzo_uint clen = sizeof(compressed);
    assert(lzo2a_999_compress(plain, sizeof(plain), compressed, &clen, work) == LZO_E_OK);
    free(work);
    csi_string_t source = { .len = (long)clen, .deflate = sizeof(plain),
        .method = LZO, .string = (char *)compressed };
    int valid = strcmp(argv[2], "valid") == 0;
    if (!strcmp(argv[2], "overflow")) source.deflate = 16;
    else if (!strcmp(argv[2], "short")) source.deflate = 80;
    else if (!strcmp(argv[2], "truncated")) source.len--;
    else if (!strcmp(argv[2], "trailing")) { compressed[clen] = 0; source.len++; }
    else if (!strcmp(argv[2], "intmax")) source.deflate = INT_MAX;
    else if (!strcmp(argv[2], "uintmax")) source.deflate = (long)UINT32_MAX;
    else if (!strcmp(argv[2], "negative")) source.deflate = -1;
    else if (!strcmp(argv[2], "string-oom")) fail_string_allocation = 1;
    else assert(valid);
    csi_t ctx = { .hooks.create_source_image = create_image };
    int success = 0;
    const unsigned char *result = NULL;
    if (!strcmp(argv[1], "file")) {
        csi_object_t object = {0};
        success = csi_file_new_from_string(&ctx, &object, &source) == CSI_STATUS_SUCCESS;
        if (success) {
            result = object.datum.file->data;
            csi_string_free(&ctx, object.datum.file->src);
            _csi_slab_free(&ctx, object.datum.file, sizeof(csi_file_t));
        }
    } else if (!strcmp(argv[1], "font")) {
        result = inflate_string(&ctx, &source);
        success = result != NULL;
    } else {
        assert(!strcmp(argv[1], "image"));
        csi_object_t object = { .type = CSI_OBJECT_TYPE_STRING, .datum.string = &source };
        cairo_surface_t *image = NULL;
        success = _image_read_raw(&ctx, &object, CAIRO_FORMAT_A8,
            (int)source.deflate, 1, &image) == CSI_STATUS_SUCCESS;
        if (success) { result = cairo_image_surface_get_data(image); cairo_surface_destroy(image); }
    }
    int guards = guard_valid();
    int contents = !valid || (result && !memcmp(result, plain, sizeof(plain)));
    int passed = success == valid && guards && contents && !invalid_allocation && slab_live == 0;
    printf("%s/%s: %s (success=%d guard=%d content=%d invalid-allocation=%d slab-live=%d)\n",
        argv[1], argv[2], passed ? "PASS" : "FAIL", success, guards, contents, invalid_allocation, slab_live);
    free(allocation);
    return passed ? 0 : 1;
}
#endif
