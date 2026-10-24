/* SPDX-License-Identifier: MIT */
/* Origin: EmberBSD contributors (AI-assisted). Actual-source PRIME controls. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { \
   fprintf(stderr, "FAIL:%d %s\n", __LINE__, #x); exit(1); \
} } while (0)
#define HAVE_LIBDRM 1
#define DETECT_OS_POSIX 1
#define PIPE_MEMORY_FD 1
/* No HAVE_LINUX_UDMABUF_H: this models a native POSIX importer. */
enum pipe_format { TEST_FORMAT };
struct list_head { struct list_head *next, *prev; };
typedef int mtx_t;
enum { mtx_plain, thrd_success = 0, thrd_error = 1 };
struct pipe_screen;
struct pipe_memory_allocation { int unused; };
struct sw_winsys { int fixture_tag; };
struct sw_displaytarget { int unused; };
struct winsys_handle { int handle; unsigned offset, size; };
#include "layouts.h"

static unsigned allocs, frees, dup_calls, closes, map_calls, unmaps, opaque;
static unsigned inits, destroys, planes, published;
static bool fail_alloc, fail_dup, fail_seek, fail_map, fail_init, fail_plane;
static unsigned char pixels[4096];
static struct kms_sw_plane test_plane;

static void *
allocate(size_t size)
{
   if (fail_alloc)
      return NULL;
   void *p = calloc(1, size);
   CHECK(p);
   allocs++;
   return p;
}

static void
release(void *p)
{
   CHECK(p && allocs > frees);
   frees++;
   free(p);
}

#define CALLOC_STRUCT(t) allocate(sizeof(struct t))
#define FREE(p) release(p)

static int
duplicate(int fd)
{
   CHECK(fd == 100);
   dup_calls++;
   return fail_dup ? -1 : 101;
}

static int
close_copy(int fd)
{
   CHECK(fd == 101); /* Never close the caller's descriptor. */
   closes++;
   return 0;
}

static off_t
seek_buffer(int fd, off_t offset, int whence)
{
   CHECK((fd == 100 || fd == 101) && offset == 0);
   CHECK(whence == SEEK_SET || whence == SEEK_END);
   return fail_seek ? -1 : (whence == SEEK_END ? (off_t)sizeof(pixels) : 0);
}

static void *
map_buffer(const void *addr, size_t size, int prot, int flags, int fd, off_t offset)
{
   CHECK(addr == NULL && size == sizeof(pixels) && fd == 101 && offset == 0);
   CHECK(prot == (PROT_READ | PROT_WRITE) && flags == MAP_SHARED);
   map_calls++;
   return fail_map ? MAP_FAILED : pixels;
}

static int
unmap_buffer(const void *addr, size_t size)
{
   CHECK(addr == pixels && size == sizeof(pixels));
   unmaps++;
   return 0;
}

static bool
opaque_import(int fd, void **addr, uint64_t *size, const char *id)
{
   (void)fd; (void)addr; (void)size; (void)id;
   opaque++;
   return false; /* An opaque file is not a native exported DMA-BUF. */
}

static void
opaque_free(void *p)
{
   (void)p;
   CHECK(false);
}

static int
mtx_init(mtx_t *lock, int type)
{
   CHECK(type == mtx_plain && *lock == 0);
   inits++;
   if (fail_init)
      return thrd_error;
   *lock = 42;
   return thrd_success;
}

static void
mtx_destroy(mtx_t *lock)
{
   CHECK(*lock == 42);
   *lock = 0;
   destroys++;
}

static void
list_inithead(struct list_head *head)
{
   head->next = head->prev = head;
}

static void
list_add(const struct list_head *entry, const struct list_head *head)
{
   CHECK(head->next != NULL && entry != NULL);
   published++;
}

static int
drmPrimeFDToHandle(int drm, int fd, uint32_t *handle)
{
   CHECK(drm == 88 && fd == 100);
   *handle = 7;
   return 0;
}

static struct kms_sw_displaytarget *
kms_sw_displaytarget_find_and_ref(const struct kms_sw_winsys *ws, unsigned handle)
{
   CHECK(ws->fd == 88 && handle == 7);
   return NULL; /* Exercise a new BO rather than the cached-object path. */
}

static struct kms_sw_plane *
get_plane(struct kms_sw_displaytarget *dt, enum pipe_format format,
          unsigned width, unsigned height, unsigned stride, unsigned offset)
{
   CHECK(dt->map_lock == 42); /* A zero-filled mutex is not initialized. */
   CHECK(format == TEST_FORMAT && width == 16 && height == 16);
   CHECK(stride == 64 && offset == 0);
   planes++;
   test_plane.dt = dt;
   return fail_plane ? NULL : &test_plane;
}

static struct kms_sw_winsys *kms_sw_winsys(struct sw_winsys *ws)
{ CHECK(ws->fixture_tag == 88); return (struct kms_sw_winsys *)ws; }
static struct sw_displaytarget *sw_displaytarget(struct kms_sw_plane *p)
{ return (struct sw_displaytarget *)p; }

#define os_dupfd_cloexec duplicate
#define os_import_memory_fd opaque_import
#define os_free_fd opaque_free
#define close close_copy
#define lseek seek_buffer
#define mmap map_buffer
#define munmap unmap_buffer
static const char *driver_id = "prime-import-contract";
#include "bodies.h"

static void
reset(void)
{
   CHECK(allocs == frees);
   allocs = frees = dup_calls = closes = map_calls = unmaps = opaque = 0;
   inits = destroys = planes = published = 0;
   fail_alloc = fail_dup = fail_seek = fail_map = fail_init = fail_plane = false;
}

static void
import_cases(void)
{
   for (unsigned fault = 0; fault < 5; fault++) {
      struct pipe_screen *screen = NULL;
      struct pipe_memory_allocation *memory = NULL;
      uint64_t size = 123;
      reset();
      fail_alloc = fault == 1; fail_dup = fault == 2;
      fail_seek = fault == 3; fail_map = fault == 4;
      bool ok = llvmpipe_import_memory_fd(screen, 100, &memory, &size, true);
      CHECK(ok == (fault == 0));
      CHECK(opaque == 0);
      if (ok) {
         const struct llvmpipe_memory_allocation *allocation = (void *)memory;
         CHECK(size == sizeof(pixels) && allocation->cpu_addr == pixels);
         CHECK(allocation->type == LLVMPIPE_MEMORY_FD_TYPE_DMA_BUF);
         CHECK(allocation->fd == 101 && allocation->mem_fd == -1);
         llvmpipe_free_memory_fd(screen, memory);
         CHECK(unmaps == 1 && closes == 1 && map_calls == 1);
      } else {
         CHECK(memory == NULL && size == 123 && unmaps == 0);
         CHECK(closes == (unsigned)(fault == 3 || fault == 4));
      }
      CHECK(allocs == frees);
   }
}

static void
lock_cases(void)
{
   for (unsigned mapped = 0; mapped < 2; mapped++) {
      for (unsigned fault = 0; fault < 5; fault++) {
         if (mapped && fault == 3)
            continue; /* The mapped constructor does not seek. */
         struct kms_sw_winsys ws = { .fd = 88 };
         struct winsys_handle handle = { .handle = 100, .size = sizeof(pixels) };
         struct kms_sw_plane *plane;
         reset();
         ws.base.fixture_tag = 88;
         list_inithead(&ws.bo_list);
         fail_alloc = fault == 1; fail_init = fault == 2;
         fail_seek = fault == 3; fail_plane = fault == 4;
         if (mapped)
            plane = (void *)kms_sw_displaytarget_create_mapped(&ws.base, 0,
               TEST_FORMAT, 16, 16, 64, pixels, &handle);
         else
            plane = kms_sw_displaytarget_add_from_prime(&ws, 100,
               TEST_FORMAT, 16, 16, 64, 0);
         CHECK((plane != NULL) == (fault == 0));
         CHECK(inits == (unsigned)(fault != 1));
         if (plane) {
            CHECK(published == 1 && planes == 1 && destroys == 0);
            mtx_destroy(&plane->dt->map_lock);
            release(plane->dt);
         } else {
            CHECK(published == 0);
            CHECK(destroys == (unsigned)(fault == 3 || fault == 4));
         }
         CHECK(allocs == frees);
      }
   }
}

int
main(int argc, char **argv)
{
   CHECK(argc == 2);
   if (strcmp(argv[1], "import") == 0)
      import_cases();
   else {
      CHECK(strcmp(argv[1], "lock") == 0);
      lock_cases();
   }
   puts("PASS: actual-source POSIX import or KMS mutex lifetime controls");
   return 0;
}
