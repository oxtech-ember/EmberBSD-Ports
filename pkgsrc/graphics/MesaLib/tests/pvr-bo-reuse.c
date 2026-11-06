/* SPDX-License-Identifier: BSD-2-Clause */
/* The BO owner is real Mesa code. Only its winsys and host allocation are fake. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include "util/list.h"

typedef int VkResult;
typedef pthread_mutex_t simple_mtx_t;
typedef struct { uint64_t addr; } pvr_dev_addr_t;
#define ALWAYS_INLINE inline
#define BITFIELD_BIT(n) (1U << (n))
#define VK_SUCCESS 0
#define VK_ERROR_OUT_OF_HOST_MEMORY (-1)
#define VK_ERROR_OUT_OF_DEVICE_MEMORY (-2)
#define VK_SYSTEM_ALLOCATION_SCOPE_OBJECT 0
#define PVR_WINSYS_BO_FLAG_CPU_ACCESS 1
#define PVR_WINSYS_BO_FLAG_GPU_UNCACHED 2
#define PVR_WINSYS_BO_FLAG_PM_FW_PROTECT 4
#define PVR_WINSYS_BO_TYPE_GPU 0
#define VG(x)
#define mtx_plain 0
#define simple_mtx_init(m, f) assert(!pthread_mutex_init(m, NULL))
#define simple_mtx_lock(m) assert(!pthread_mutex_lock(m))
#define simple_mtx_unlock(m) assert(!pthread_mutex_unlock(m))
#define simple_mtx_destroy(m) assert(!pthread_mutex_destroy(m))
#define MAX2(a, b) ((a) > (b) ? (a) : (b))
#define ALIGN_POT(n, a) (((n) + (a) - 1) & ~((a) - 1))
#define p_atomic_inc(p) __atomic_add_fetch(p, 1, __ATOMIC_RELAXED)
#define p_atomic_read(p) __atomic_load_n(p, __ATOMIC_RELAXED)
#define p_atomic_set(p, v) __atomic_store_n(p, v, __ATOMIC_RELAXED)
#define p_atomic_dec_zero(p) (__atomic_sub_fetch(p, 1, __ATOMIC_ACQ_REL) == 0)
#define PVR_DEV_ADDR_OFFSET(base, off) ((pvr_dev_addr_t){(base).addr + (off)})

struct pvr_winsys_heap { unsigned id; };
struct pvr_winsys_bo { uint64_t size; void *map, *storage; };
struct pvr_winsys_vma { pvr_dev_addr_t dev_addr; uint64_t size; };
struct pvr_device_info { unsigned unused; };
struct pvr_physical_device { struct pvr_device_info dev_info; };
struct pvr_winsys;
struct fake_ops {
   VkResult (*buffer_create)(struct pvr_winsys *, uint64_t, uint64_t, int, uint32_t, struct pvr_winsys_bo **);
   VkResult (*buffer_map)(struct pvr_winsys_bo *, void *);
   void (*buffer_unmap)(struct pvr_winsys_bo *, bool);
   void (*buffer_destroy)(struct pvr_winsys_bo *);
   VkResult (*heap_alloc)(struct pvr_winsys_heap *, uint64_t, uint64_t, struct pvr_winsys_vma **);
   void (*heap_free)(struct pvr_winsys_vma *);
   VkResult (*vma_map)(struct pvr_winsys_vma *, struct pvr_winsys_bo *, uint64_t, uint64_t, void *);
   void (*vma_unmap)(struct pvr_winsys_vma *);
};
struct pvr_winsys { struct fake_ops *ops; };
/* HEADER */
#ifndef PVR_BO_ALLOC_FLAG_CACHE
#define PVR_BO_ALLOC_FLAG_CACHE 0
/* Keep the pre-cache source usable as the failing causal control. */
#define PVR_BO_CACHE_MAX_BYTES (1024U * 1024U)
#define PVR_BO_CACHE_MAX_COUNT 16U
struct pvr_bo_cache { int unused; };
static void pvr_bo_cache_init(struct pvr_device *device) {}
static void pvr_bo_cache_fini(struct pvr_device *device) {}
static void pvr_bo_cache_flush(struct pvr_device *device) {}
#endif
struct pvr_device {
   struct { int alloc; } vk;
   struct pvr_physical_device *pdevice;
   struct pvr_winsys *ws;
   struct pvr_bo_store *bo_store;
   struct pvr_bo_cache bo_cache;
};
static unsigned created, destroyed, mapped, unmapped;
static uint64_t live_bytes;
static bool fail_create;
static unsigned fail_once;
static unsigned create_attempts;
static struct pvr_device *release_device;
static struct pvr_bo *release_during_destroy;
static VkResult vk_error(struct pvr_device *d, VkResult r) { return r; }
static void *vk_alloc(void *a, size_t n, size_t align, int scope) { return malloc(n); }
static void vk_free(void *a, void *p) { free(p); }
static bool util_is_power_of_two_nonzero(uint32_t n) { return n && !(n & (n - 1)); }
static unsigned pvr_get_slc_cache_line_size(const struct pvr_device_info *d) { return 64; }
static struct pvr_bo *pvr_bo_alloc_bo(const struct pvr_device *d) { return calloc(1, sizeof(struct pvr_bo)); }
static void pvr_bo_free_bo(const struct pvr_device *d, struct pvr_bo *bo) { free(bo); }
static void pvr_bo_store_insert(struct pvr_bo_store *s, struct pvr_bo *b) {}
static void pvr_bo_store_remove(struct pvr_bo_store *s, struct pvr_bo *b) {}
static void pvr_bo_destroy(struct pvr_device *device, struct pvr_bo *bo);
/* SOURCE */

static VkResult create(struct pvr_winsys *ws, uint64_t size, uint64_t align,
                       int type, uint32_t flags, struct pvr_winsys_bo **out)
{
   __atomic_add_fetch(&create_attempts, 1, __ATOMIC_RELAXED);
   if (fail_create || fail_once) {
      if (fail_once) fail_once--;
      return VK_ERROR_OUT_OF_DEVICE_MEMORY;
   }
   struct pvr_winsys_bo *b = calloc(1, sizeof(*b));
   assert(b);
   b->size = ALIGN_POT(ALIGN_POT(size, align), UINT64_C(4096));
   assert(!posix_memalign(&b->storage, MAX2(align, UINT64_C(4096)), b->size));
   memset(b->storage, 0xcd, b->size);
   *out = b;
   __atomic_add_fetch(&created, 1, __ATOMIC_RELAXED);
   __atomic_add_fetch(&live_bytes, b->size, __ATOMIC_RELAXED);
   return VK_SUCCESS;
}
static VkResult map(struct pvr_winsys_bo *b, void *arg)
{ b->map = b->storage; __atomic_add_fetch(&mapped, 1, __ATOMIC_RELAXED); return VK_SUCCESS; }
static void unmap(struct pvr_winsys_bo *b, bool flush)
{ b->map = NULL; __atomic_add_fetch(&unmapped, 1, __ATOMIC_RELAXED); }
static void destroy(struct pvr_winsys_bo *b)
{
   if (release_during_destroy) {
      struct pvr_bo *later = release_during_destroy;
      release_during_destroy = NULL;
      pvr_bo_free(release_device, later);
   }
   __atomic_sub_fetch(&live_bytes, b->size, __ATOMIC_RELAXED);
   free(b->storage); free(b);
   __atomic_add_fetch(&destroyed, 1, __ATOMIC_RELAXED);
}
static VkResult heap_alloc(struct pvr_winsys_heap *h, uint64_t size, uint64_t align, struct pvr_winsys_vma **v)
{ *v = calloc(1, sizeof(**v)); assert(*v); (*v)->size = size; return VK_SUCCESS; }
static void heap_free(struct pvr_winsys_vma *v) { free(v); }
static VkResult vma_map(struct pvr_winsys_vma *v, struct pvr_winsys_bo *b, uint64_t off, uint64_t size, void *arg)
{ v->dev_addr.addr = (uintptr_t)b->storage; return VK_SUCCESS; }
static void vma_unmap(struct pvr_winsys_vma *v) {}

static void frame(struct pvr_suballocator *a)
{
   struct pvr_suballoc_bo *b[4];
   for (unsigned i = 0; i < 4; i++) {
      assert(pvr_bo_suballoc(a, 100000, 64, true, &b[i]) == VK_SUCCESS);
      unsigned char *mem = pvr_bo_suballoc_get_map_addr(b[i]);
      for (unsigned j = 0; j < 100000; j++) assert(mem[j] == 0);
      memset(mem, (int)i + 1, 100000);
   }
   for (unsigned i = 0; i < 4; i++) {
      unsigned char *mem = pvr_bo_suballoc_get_map_addr(b[i]);
      for (unsigned j = 0; j < 100000; j++) assert(mem[j] == i + 1);
      pvr_bo_suballoc_free(b[i]);
   }
}

struct thread_args { struct pvr_device *device; struct pvr_winsys_heap *heap; unsigned id; };
static pthread_barrier_t barrier;
static void *thread_run(void *data)
{
   struct thread_args *arg = data;
   for (unsigned n = 0; n < 64; n++) {
      struct pvr_bo *bo;
      assert(pvr_bo_alloc(arg->device, arg->heap, 16384, 64,
                         PVR_BO_ALLOC_FLAG_CPU_MAPPED | PVR_BO_ALLOC_FLAG_CACHE, &bo) == VK_SUCCESS);
      memset(bo->bo->map, (int)arg->id, 16384);
      pthread_barrier_wait(&barrier);
      for (unsigned j = 0; j < 16384; j++) assert(((unsigned char *)bo->bo->map)[j] == arg->id);
      pthread_barrier_wait(&barrier);
      pvr_bo_free(arg->device, bo);
   }
   return NULL;
}

int main(void)
{
   struct fake_ops ops = {create, map, unmap, destroy, heap_alloc, heap_free, vma_map, vma_unmap};
   struct pvr_winsys ws = {&ops};
   struct pvr_physical_device physical = {0};
   struct pvr_device device = {.ws = &ws, .pdevice = &physical};
   struct pvr_winsys_heap heap = {1};
   struct pvr_suballocator a;
   pvr_bo_cache_init(&device);
   pvr_bo_suballocator_init(&a, &heap, &device, 131072);
   frame(&a); frame(&a);
   unsigned warm = created;
   for (unsigned n = 0; n < 20; n++) frame(&a);
   if (created != warm) {
      fprintf(stderr, "FAIL: stable four-block frames allocate again: warm=%u final=%u\n", warm, created);
      return 1;
   }
   struct pvr_bo *small, *next;
   uint64_t flags = PVR_BO_ALLOC_FLAG_CPU_MAPPED | PVR_BO_ALLOC_FLAG_CACHE;
   assert(pvr_bo_alloc(&device, &heap, 4096, 64, flags, &small) == VK_SUCCESS);
   pvr_dev_addr_t address = small->vma->dev_addr;
   pvr_bo_free(&device, small);
   warm = created;
   assert(pvr_bo_alloc(&device, &heap, 4096, 64, flags, &next) == VK_SUCCESS);
   assert(created == warm && next->vma->dev_addr.addr == address.addr);
   pvr_bo_free(&device, next);
   pvr_bo_suballocator_fini(&a);

   /* A retained command reference excludes reuse, including its contents. */
   assert(pvr_bo_alloc(&device, &heap, 4096, 64, flags, &small) == VK_SUCCESS);
   memset(small->bo->map, 0x5a, 4096);
   p_atomic_inc(&small->ref_count);
   pvr_bo_free(&device, small);
   assert(pvr_bo_alloc(&device, &heap, 4096, 64, flags, &next) == VK_SUCCESS);
   assert(next != small && next->bo->map != small->bo->map);
   memset(next->bo->map, 0xa5, 4096);
   for (unsigned j = 0; j < 4096; j++) assert(((unsigned char *)small->bo->map)[j] == 0x5a);
   pvr_bo_free(&device, next); pvr_bo_free(&device, small);

   /* Each mapping attribute is part of the key. */
   struct pvr_winsys_heap other_heap = {2};
   for (unsigned variant = 0; variant < 4; variant++) {
      pvr_bo_cache_flush(&device);
      assert(pvr_bo_alloc(&device, &heap, 4096, 64, flags, &small) == VK_SUCCESS);
      pvr_bo_free(&device, small); warm = created;
      assert(pvr_bo_alloc(&device, variant == 0 ? &other_heap : &heap,
                         variant == 1 ? 4097 : 4096, variant == 2 ? 8192 : 64,
                         variant == 3 ? flags | PVR_BO_ALLOC_FLAG_GPU_UNCACHED : flags, &next) == VK_SUCCESS);
      assert(created == warm + 1);
      assert(next->vma->dev_addr.addr % (variant == 2 ? 8192 : 64) == 0);
      pvr_bo_free(&device, next);
   }

   /* Memory pressure releases only idle BOs and retries once. */
   unsigned attempts = create_attempts;
   fail_once = 1;
   assert(pvr_bo_alloc(&device, &heap, 12345, 64, flags, &next) == VK_SUCCESS);
   assert(create_attempts == attempts + 2);
   pvr_bo_free(&device, next);
   fail_create = true;
   attempts = create_attempts;
   next = (struct pvr_bo *)(uintptr_t)1;
   assert(pvr_bo_alloc(&device, &heap, 54321, 64, flags, &next) == VK_ERROR_OUT_OF_DEVICE_MEMORY);
   assert(create_attempts == attempts + 2);
   assert(next == (struct pvr_bo *)(uintptr_t)1 && live_bytes == 0);
   fail_create = false;

   /* Bound idle bytes and objects, including real winsys page rounding. */
   struct pvr_bo *batch[40];
   for (unsigned mode = 0; mode < 2; mode++) {
      for (unsigned i = 0; i < 40; i++)
         assert(pvr_bo_alloc(&device, &heap, mode ? 131072 : 4096, 64, flags, &batch[i]) == VK_SUCCESS);
      for (unsigned i = 0; i < 40; i++) pvr_bo_free(&device, batch[i]);
      assert(created - destroyed <= PVR_BO_CACHE_MAX_COUNT &&
             live_bytes <= PVR_BO_CACHE_MAX_BYTES);
      pvr_bo_cache_flush(&device);
      assert(live_bytes == 0);
   }
   assert(pvr_bo_alloc(&device, &heap, 1, 2 * PVR_BO_CACHE_MAX_BYTES, flags, &next) == VK_SUCCESS);
   pvr_bo_free(&device, next); assert(live_bytes == 0);

   /* A flush drains its initial snapshot, not BOs freed during destruction. */
   assert(pvr_bo_alloc(&device, &heap, 4096, 64, flags, &small) == VK_SUCCESS);
   assert(pvr_bo_alloc(&device, &heap, 65536, 64, flags, &next) == VK_SUCCESS);
   pvr_bo_free(&device, small);
   release_device = &device; release_during_destroy = next;
   pvr_bo_cache_flush(&device);
   assert(!release_during_destroy && live_bytes == 65536);
   pvr_bo_cache_flush(&device); assert(live_bytes == 0);

   pthread_t threads[4];
   struct thread_args thread_data[4];
   assert(!pthread_barrier_init(&barrier, NULL, 4));
   for (unsigned i = 0; i < 4; i++) {
      thread_data[i] = (struct thread_args){&device, &heap, i + 1};
      assert(!pthread_create(&threads[i], NULL, thread_run, &thread_data[i]));
   }
   for (unsigned i = 0; i < 4; i++) assert(!pthread_join(threads[i], NULL));
   assert(!pthread_barrier_destroy(&barrier));
   pvr_bo_cache_fini(&device);
   assert(created == destroyed && mapped == unmapped && live_bytes == 0);
   puts("PASS: frame reuse, live references, zero fill, exact keys, OOM, limits, threads, teardown");
   return 0;
}
