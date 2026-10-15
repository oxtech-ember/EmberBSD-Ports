// SPDX-License-Identifier: MIT
// The included functions are unmodified pinned Mesa source.
// Only image allocation, DRI export, tracing and Wayland boundaries are doubled.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>
#ifdef NDEBUG
#error This contract requires active assertions.
#endif

typedef int EGLBoolean;
typedef int EGLint;
#define EGL_TRUE 1
#define EGL_FALSE 0
#define EGL_BAD_ALLOC 0x3003
#define EGL_BAD_NATIVE_WINDOW 0x300B
#define EGL_PBUFFER_BIT 1
#define PIPE_FORMAT_NONE 0
#define __DRI_IMAGE_USE_SHARE 1
#define __DRI_IMAGE_USE_BACKBUFFER 2
#define __DRI_IMAGE_USE_PROTECTED 4
#define __DRI_IMAGE_USE_LINEAR 8
#define __DRI_IMAGE_BUFFER_FRONT 1
#define __DRI_IMAGE_BUFFER_BACK 2
#define __DRI_IMAGE_PRIME_LINEAR_BUFFER 1
#define __DRI_YUV_COLOR_SPACE_UNDEFINED 0
#define __DRI_YUV_RANGE_UNDEFINED 0
#define __DRI_YUV_CHROMA_SITING_UNDEFINED 0
#define __DRI_IMAGE_ATTRIB_NUM_PLANES 0x200B
#define __DRI_IMAGE_ATTRIB_FD 0x2007
#define __DRI_IMAGE_ATTRIB_STRIDE 0x2000
#define __DRI_IMAGE_ATTRIB_OFFSET 0x2008
#define __DRI_IMAGE_ATTRIB_FOURCC 0x2006
#define DRM_FORMAT_MOD_LINEAR 0
#define BUFFER_TRIM_AGE_HYSTERESIS 20
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define BITSET_TEST(bitmap, index) (((bitmap) & (1u << (index))) != 0)
#define MESA_TRACE_FUNC_FLOW(flow) ((void)(flow))
#define MESA_TRACE_FUNC() ((void)0)

struct mesa_trace_flow { int value; };
struct dri_image { int value; };
struct wl_buffer { int value; };
struct pipe_screen { void *resource_create_with_modifiers; };
struct dri_screen { struct { struct pipe_screen *screen; } base; };
struct dri_drawable { int value; };
struct dri2_egl_surface;
struct dri2_egl_display;
typedef struct { struct dri2_egl_display *driver; } _EGLDisplay;
typedef struct {
    struct { _EGLDisplay *Display; } Resource;
    int Width, Height, SwapInterval, Type;
    bool ProtectedContent;
} _EGLSurface;
typedef struct { int value; } _EGLContext;
struct wl_window { int width, height, dx, dy, attached_width, attached_height; };
struct loader_wayland_buffer { struct wl_buffer *buffer; struct mesa_trace_flow flow; };
struct dri2_egl_buffer {
    struct loader_wayland_buffer wayland_buffer;
    struct dri_image *dri_image, *linear_copy;
    bool locked, wl_release;
    int age;
};
struct dri2_egl_surface {
    _EGLSurface base;
    struct dri2_egl_buffer color_buffers[4], *back, *current;
    struct dri_image *front;
    struct wl_window *wl_win;
    struct dri_drawable *dri_drawable;
    void *wl_dmabuf_feedback, *wl_queue, *throttle_callback, *wl_dpy_wrapper;
    struct { void *wrapper; } wayland_surface;
    int wayland_presentation, dx, dy, format;
    bool resized, received_dmabuf_feedback;
};
struct dri2_egl_display {
    int fd_render_gpu, fd_display_gpu;
    struct { unsigned formats_bitmap; } formats;
    void *wl_dpy;
    struct dri_screen *dri_screen_render_gpu, *dri_screen_display_gpu;
    struct { struct dri_drawable *(*get_dri_drawable)(_EGLSurface *); } *vtbl;
};
struct dri2_egl_context { void *dri_context; };
struct __DRIimageList { struct dri_image *back, *front; unsigned image_mask; };
static struct { unsigned pipe_format, alt_pipe_format; } dri2_wl_visuals[] = {{1, 1}};
static struct dri_image image_storage, partial_storage;
static struct wl_buffer buffer_storage;
static int allocation_calls, invalid_images, creates, attaches, commits, error_code;
static bool allocation_fails, linear_fails;
static int throttle_listener, wl_buffer_listener;
static struct dri2_egl_display *dri2_egl_display(_EGLDisplay *d) { return d->driver; }
static struct dri2_egl_surface *dri2_egl_surface(_EGLSurface *s) { return (void *)s; }
static int _eglError(int code, const char *where) { (void)where; error_code=code; return EGL_FALSE; }
static int dri2_wl_visual_idx_from_fourcc(int format) { (void)format; return 0; }
static int dri2_wl_visual_idx_from_pipe_format(int format) { (void)format; return 0; }
static void wl_display_dispatch_queue_pending(void *d, void *q) { (void)d; (void)q; }
static int wl_display_roundtrip_queue(void *d, void *q) { (void)d; (void)q; return -1; }
static uint64_t *get_surface_specific_modifiers(struct dri2_egl_surface *s, int *count) { (void)s; *count=0; return NULL; }
static void create_dri_image_from_formats(struct dri2_egl_surface *s, unsigned format, int flags, uint64_t *mods, int count) {
    (void)format; (void)flags; (void)mods; (void)count;
    allocation_calls++; s->back->dri_image=allocation_fails ? NULL : &image_storage;
}
static void create_dri_image_from_dmabuf_feedback(struct dri2_egl_surface *s, unsigned f, int u, uint64_t *m, int n) {
    create_dri_image_from_formats(s,f,u,m,n);
}
static struct dri_image *dri_create_image_with_modifiers(struct dri_screen *s, int width, int height, unsigned format, unsigned flags, const uint64_t *modifiers, unsigned count, void *data) {
    (void)s; (void)width; (void)height; (void)format; (void)flags; (void)modifiers; (void)count; (void)data;
    allocation_calls++; return linear_fails ? NULL : &partial_storage;
}
static bool dri2_query_image(struct dri_image *image, int attr, int *value) { (void)attr; if (!image) {invalid_images++; return false;} *value=1; return true; }
static struct dri_image *dri2_from_planar(struct dri_image *image, int plane, void *data) { (void)plane; (void)data; return image; }
static struct dri_image *dri2_from_dma_bufs(struct dri_screen *s, ...) { (void)s; return &partial_storage; }
static void dri2_destroy_image(struct dri_image *image) { assert(image); }
static void loader_wayland_buffer_set_flow(struct loader_wayland_buffer *b, struct mesa_trace_flow *f) { b->flow=*f; }
static void loader_wayland_buffer_destroy(struct loader_wayland_buffer *b) { b->buffer=NULL; }
static void dri2_wl_release_buffers(struct dri2_egl_surface *s) { for (unsigned i=0;i<4;i++) {s->color_buffers[i].dri_image=NULL;s->color_buffers[i].linear_copy=NULL;} }
static void dri2_flush_drawable_for_swapbuffers(_EGLDisplay *d, _EGLSurface *s) { (void)d; (void)s; }
static void dri_invalidate_drawable(struct dri_drawable *d) { (void)d; }
static int throttle(struct dri2_egl_display *d, struct dri2_egl_surface *s) { (void)d; s->throttle_callback=NULL; return 0; }
static void *wl_surface_frame(void *s) { return s; }
static void wl_callback_add_listener(void *c, int *l, struct dri2_egl_surface *s) { (void)c; (void)l; (void)s; }
static struct wl_buffer *create_wl_buffer(struct dri2_egl_display *d, struct dri2_egl_surface *s, struct dri_image *image) {
    (void)d; (void)s; creates++;
    // Observe the invalid boundary without dereferencing NULL in the baseline.
    if (!image) {invalid_images++; return NULL;}
    return &buffer_storage;
}
static void loader_wayland_wrap_buffer(struct loader_wayland_buffer *b, struct wl_buffer *w) { b->buffer=w; }
static void wl_buffer_add_listener(struct wl_buffer *b, int *l, struct dri2_egl_surface *s) { (void)b; (void)l; (void)s; }
static void wl_surface_attach(void *s, struct wl_buffer *b, int x, int y) { (void)s; (void)x; (void)y; assert(b); attaches++; }
static bool try_damage_buffer(struct dri2_egl_surface *s, const EGLint *r, EGLint n) { (void)s; (void)r; (void)n; return true; }
static void wl_surface_damage(void *s, int x, int y, int w, int h) { (void)s; (void)x; (void)y; (void)w; (void)h; }
static _EGLContext *_eglGetCurrentContext(void) { static _EGLContext c; return &c; }
static struct dri2_egl_context *dri2_egl_context(_EGLContext *c) { (void)c; static struct dri2_egl_context d; return &d; }
static void dri2_blit_image(void *ctx, ...) { (void)ctx; }
static void dri_flush_drawable(struct dri_drawable *d) { (void)d; }
static void loader_wayland_presentation_feedback(int *p, struct loader_wayland_buffer *b, void *x) { (void)p; (void)b; (void)x; }
static void wl_surface_commit(void *s) { (void)s; commits++; }
static void *wl_display_sync(void *d) { return d; }
static void wl_display_flush(void *d) { (void)d; }

#include "wayland-methods.inc"

static struct dri_drawable *get_drawable(_EGLSurface *s) { return dri2_egl_surface(s)->dri_drawable; }
static int check_case(bool different_gpu)
{
    struct pipe_screen pipe={0};
    struct dri_screen screen={{&pipe}};
    struct dri2_egl_display d={.fd_render_gpu=8,.fd_display_gpu=different_gpu?9:8,.formats={1},.dri_screen_render_gpu=&screen};
    __typeof__(*d.vtbl) vtbl={.get_dri_drawable=get_drawable}; d.vtbl=&vtbl;
    _EGLDisplay display={.driver=&d};
    struct wl_window window={.width=1280,.height=1024};
    struct dri2_egl_surface s={.base={.Resource={&display},.Width=1280,.Height=1024},.wl_win=&window};
    struct __DRIimageList images={0};
    allocation_calls=invalid_images=creates=attaches=commits=error_code=0;
    allocation_fails=true; linear_fails=different_gpu;
    // A partial slot remains owned by the surface even after its alias is reset.
    if (!different_gpu) s.color_buffers[3].linear_copy=&partial_storage;
    int result=image_get_buffers(NULL,0,NULL,&s,__DRI_IMAGE_BUFFER_BACK,&images);
    assert(result==0);
    assert(error_code==EGL_BAD_ALLOC);
    error_code=0;
    result=dri2_wl_swap_buffers_with_damage(&display,&s.base,NULL,0);
    assert(result==EGL_FALSE);
    if (invalid_images || creates || attaches || commits || allocation_calls!=2 || s.back || s.current || error_code!=EGL_BAD_ALLOC) {
        fprintf(stderr,"FAIL: allocation failure leaves a usable back alias (different_gpu=%d, allocations=%d, invalid_images=%d)\n",different_gpu,allocation_calls,invalid_images);
        return 1;
    }
    if (!different_gpu) assert(s.color_buffers[3].linear_copy==&partial_storage);
    for (unsigned i=0;i<4;i++) assert(!s.color_buffers[i].locked);
    // Repeated OOM must keep failing. Recovery must retry and publish only a complete image.
    result=image_get_buffers(NULL,0,NULL,&s,__DRI_IMAGE_BUFFER_BACK,&images);
    assert(result==0);
    assert(!s.back && allocation_calls==3);
    allocation_fails=linear_fails=false; error_code=0;
    result=image_get_buffers(NULL,0,NULL,&s,__DRI_IMAGE_BUFFER_BACK,&images);
    assert(result==1);
    assert(s.back && s.back->dri_image && s.back->locked && images.back==s.back->dri_image);
    if (different_gpu) assert(s.back->linear_copy);
    int successful_allocations=allocation_calls;
    result=dri2_wl_swap_buffers_with_damage(&display,&s.base,NULL,0);
    assert(result==EGL_TRUE);
    assert(!s.back && s.current && s.current->dri_image && allocation_calls==successful_allocations);
    assert(invalid_images==0 && creates==1 && attaches==1 && commits==1 && error_code==0);
    return 0;
}
int main(void)
{
    int single=check_case(false);
    int multi=check_case(true);
    if (single || multi) return 1;
    puts("PASS: actual Wayland buffer OOM/retry/recovery and swap; no invalid image reaches export");
    return 0;
}
