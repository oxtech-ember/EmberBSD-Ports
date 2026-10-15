/* SPDX-License-Identifier: MIT
 * Run the real Mesa screen lifecycle and cache drain functions.
 * Double hardware, allocation, and screen-service boundaries explicitly.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "list.h"

#define CHECK(x, msg) do { if (!(x)) { fprintf(stderr, "FAIL: %s\n", msg); _Exit(1); } } while (0)
enum { thrd_success, thrd_error, mtx_plain };
typedef struct { pthread_mutex_t native; bool live; unsigned id; } mtx_t;
static unsigned init_calls, destroy_calls, live_locks, allocations, tables, counters, simulators, closes, drained, cached;
static unsigned fail_init, destroy_order[2];
static bool fail_alloc, fail_table, fail_device, fail_counter;
static int
mtx_init(mtx_t *lock, int type)
{
        CHECK(type == mtx_plain && !lock->live, "mutex init contract");
        lock->id = ++init_calls;
        if (init_calls == fail_init)
                return thrd_error;
        CHECK(pthread_mutex_init(&lock->native, NULL) == 0, "native init");
        lock->live = true;
        live_locks++;
        return thrd_success;
}
static void
mtx_destroy(mtx_t *lock)
{
        CHECK(lock->live && cached == 0, "destroy only live mutex after cache drain");
        CHECK(destroy_calls < 2, "no repeated mutex destruction");
        destroy_order[destroy_calls++] = lock->id;
        CHECK(pthread_mutex_destroy(&lock->native) == 0, "native destroy");
        lock->live = false;
        live_locks--;
}
static int
mtx_lock(mtx_t *lock)
{
        CHECK(lock->live, "cache lock was not initialized before use");
        CHECK(pthread_mutex_lock(&lock->native) == 0, "native lock");
        return thrd_success;
}
static int
mtx_unlock(mtx_t *lock)
{
        CHECK(lock->live, "unlock live mutex");
        CHECK(pthread_mutex_unlock(&lock->native) == 0, "native unlock");
        return thrd_success;
}
struct pipe_screen {
        void (*destroy)(struct pipe_screen *);
        void (*get_screen_fd)(void), (*context_create)(void), (*is_format_supported)(void);
        void (*get_canonical_format)(void), (*get_name)(void), (*get_vendor)(void), (*get_device_vendor)(void);
        void (*get_disk_shader_cache)(void), (*query_dmabuf_modifiers)(void), (*is_dmabuf_modifier_supported)(void);
        void (*get_driver_query_group_info)(void), (*get_driver_query_info)(void);
        const void *nir_options[1];
        void *transfer_helper;
};
struct renderonly { void (*destroy)(struct renderonly *); };
struct v3d_bo_cache { mtx_t lock; struct list_head time_list; };
struct v3d_screen {
        struct pipe_screen base;
        struct v3d_bo_cache bo_cache;
        mtx_t bo_handles_mutex;
        int fd, devinfo, transfer_pool;
        struct renderonly *ro;
        void *bo_handles, *perfcnt, *sim_file, *compiler, *disk_cache;
        bool nonmsaa_texture_size_limit, has_csd, has_cache_flush, has_perfmon, has_cpu_queue, has_multisync;
        float heap_memory_percent;
        unsigned prim_types;
};
struct v3d_bo { struct list_head time_list; struct v3d_screen *screen; };
struct v3d_transfer { int dummy; };
struct pipe_screen_config { void *options, *options_info; };
typedef struct { const char *driverName; } driConfigFileParseParams;
#define v3d_screen(screen) ((struct v3d_screen *)(screen))
#define MESA_SHADER_COMPUTE 0
#define DRI_BOOL 1
#define OS_GPU_HEAP_SIZE_HEURISTIC -1.0f
#define BITFIELD_BIT(bit) 1U
#define MESA_TRACE_FUNC() ((void)0)
#define mesa_logd(...) ((void)0)
static void *v3d_ioctl;
#define DRM_V3D_PARAM_SUPPORTS_CSD 1
#define DRM_V3D_PARAM_SUPPORTS_CACHE_FLUSH 2
#define DRM_V3D_PARAM_SUPPORTS_PERFMON 3
#define DRM_V3D_PARAM_SUPPORTS_CPU_QUEUE 4
#define DRM_V3D_PARAM_SUPPORTS_MULTISYNC_EXT 5
static bool dump_stats;
static void v3d_bo_dump_stats(struct v3d_screen *screen) { (void)screen; }
static void
v3d_bo_remove_from_cache(struct v3d_bo_cache *cache, struct v3d_bo *bo)
{
        CHECK(cache->lock.live, "drain has live cache lock");
        list_del(&bo->time_list);
}
static void v3d_bo_free(struct v3d_bo *bo) { cached--; drained++; free(bo); }
static void *
test_rzalloc(size_t size)
{
        if (fail_alloc)
                return NULL;
        void *ptr = calloc(1, size);
        CHECK(ptr != NULL, "fixture allocation");
        allocations++;
        return ptr;
}
#define rzalloc(ctx, type) test_rzalloc(sizeof(type))
static void ralloc_free(void *ptr) { CHECK(ptr != NULL && allocations == 1, "screen freed once"); allocations--; free(ptr); }
static int test_close(int fd) { CHECK(fd == 41 && closes == 0, "owned fd closed once"); closes++; return 0; }
#define close test_close
static void *
util_hash_table_create_ptr_keys(void)
{
        if (fail_table)
                return NULL;
        tables++;
        return malloc(1);
}
static void _mesa_hash_table_destroy(void *ptr, void *callback) { CHECK(ptr && !callback && tables == 1, "table lifetime"); tables--; free(ptr); }
static bool v3d_get_device_info(int fd, int *info, void *ioctl_fn) { (void)info; (void)ioctl_fn; CHECK(fd == 41, "device fd"); return !fail_device; }
static void *v3d_perfcntrs_init(int *info, int fd) { (void)info; CHECK(fd == 41, "counter fd"); if (fail_counter) return NULL; counters++; return malloc(1); }
static void v3d_perfcntrs_fini(void *ptr) { CHECK(ptr && counters == 1, "counter lifetime"); counters--; free(ptr); }
#if USE_V3D_SIMULATOR
static void *v3d_simulator_init(int fd) { CHECK(fd == 41, "simulator fd"); simulators++; return malloc(1); }
static void v3d_simulator_destroy(void *ptr) { CHECK(ptr && simulators == 1, "simulator lifetime"); simulators--; free(ptr); }
#endif
#define driParseConfigFiles(options, info, params) ((void)(options), (void)(info), (void)(params))
#define driCheckOption(options, name, type) ((void)(options), (void)(name), (void)(type), true)
#define driQueryOptionb(...) false
#define driQueryOptionf(...) OS_GPU_HEAP_SIZE_HEURISTIC
#define slab_create_parent(...) ((void)0)
#define slab_destroy_parent(...) ((void)0)
#define v3d_has_feature(...) false
#define v3d_fence_screen_init(...) ((void)0)
#define v3d_process_debug_variable(...) ((void)0)
#define v3d_resource_screen_init(...) ((void)0)
#define v3d_compiler_init(...) NULL
#define v3d_compiler_free(...) ((void)0)
#define v3d_disk_cache_init(...) ((void)0)
#define disk_cache_destroy(...) ((void)0)
#define u_transfer_helper_destroy(...) ((void)0)
#define v3d_screen_get_compiler_options(...) NULL
#define v3d_init_shader_caps(...) ((void)0)
#define v3d_init_compute_caps(...) ((void)0)
#define v3d_init_screen_caps(...) ((void)0)
static void unused_callback(void) {}
#define v3d_screen_get_fd unused_callback
#define v3d_context_create unused_callback
#define v3d_screen_is_format_supported unused_callback
#define v3d_screen_get_compatible_tlb_format unused_callback
#define v3d_screen_get_name unused_callback
#define v3d_screen_get_vendor unused_callback
#define v3d_screen_get_disk_shader_cache unused_callback
#define v3d_screen_query_dmabuf_modifiers unused_callback
#define v3d_screen_is_dmabuf_modifier_supported unused_callback
#define v3d_get_driver_query_group_info unused_callback
#define v3d_get_driver_query_info unused_callback
#include "lifecycle.inc"

static void
reset(void)
{
        CHECK(!live_locks && !allocations && !tables && !counters && !simulators && !cached, "all owned resources released");
        init_calls = destroy_calls = closes = drained = fail_init = 0;
        fail_alloc = fail_table = fail_device = fail_counter = false;
}
static void
success(void)
{
        struct pipe_screen_config config = {0};
        struct pipe_screen *base = v3d_screen_create(41, &config, NULL);
        CHECK(base, "screen created");
        struct v3d_screen *screen = v3d_screen(base);
        CHECK(screen->bo_cache.lock.live && screen->bo_handles_mutex.live, "screen published without both initialized mutexes");
        CHECK(init_calls == 2 && live_locks == 2, "both mutexes initialized once");
        for (unsigned i = 0; i < 3; i++) {
                struct v3d_bo *bo = calloc(1, sizeof(*bo));
                CHECK(bo, "BO fixture allocation");
                bo->screen = screen;
                list_addtail(&bo->time_list, &screen->bo_cache.time_list);
                cached++;
        }
        base->destroy(base);
        CHECK(drained == 3 && destroy_calls == 2 && closes == 1, "normal destroy drains cache and destroys both mutexes");
        CHECK(destroy_order[0] == 2 && destroy_order[1] == 1, "reverse mutex destruction order");
        reset();
}
int
main(void)
{
        success();
        struct pipe_screen_config config = {0};
        for (unsigned fault = 0; fault < 6; fault++) {
                fail_alloc = fault == 0;
                fail_init = fault == 1 ? 1 : fault == 2 ? 2 : 0;
                fail_table = fault == 3;
                fail_device = fault == 4;
                fail_counter = fault == 5;
                CHECK(v3d_screen_create(41, &config, NULL) == NULL, "creation rejects failed resource initialization");
                CHECK(closes == 1, "creation error closes owned fd");
                const unsigned expected = fault < 2 ? 0 : fault == 2 ? 1 : 2;
                CHECK(destroy_calls == expected, "creation error destroys only initialized mutexes");
                if (expected)
                        CHECK(destroy_order[0] == expected, "creation unwind reverse order");
                reset();
                success();
        }
        puts("PASS: real V3D create/destroy/cache-drain; six failure stages and recovery release all owned resources");
        return 0;
}
