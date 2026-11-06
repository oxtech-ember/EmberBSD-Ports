/* SPDX-License-Identifier: MIT
 * Origin: EmberBSD contributors (AI-assisted).
 * Model only the sync backend. Production queue functions are inserted below.
 */
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

typedef int VkResult;
typedef uint64_t VkPipelineStageFlags2;
#define VK_SUCCESS 0
#define VK_ERROR_OUT_OF_HOST_MEMORY -1
#define PVR_JOB_TYPE_MAX 5
#define PVR_JOB_TYPE_QUERY 4
#define BITFIELD_BIT(i) (1u << (i))
#define vk_error(object, result) (result)
#define STACK_ARRAY(type, name, count) type *name = calloc(count, sizeof(type))
#define STACK_ARRAY_FINISH(name) free(name)
enum pvr_job_type { JOB_GEOM, JOB_FRAG, JOB_COMPUTE, JOB_TRANSFER, JOB_QUERY };
enum pvr_pipeline_stage_bits { STAGES_ALL = 31 };
struct vk_device { int unused; };
struct vk_sync { uint64_t dependencies; };
struct vk_sync_wait { struct vk_sync *sync; VkPipelineStageFlags2 stage_mask; uint64_t wait_value; };
struct vk_sync_signal { struct vk_sync *sync; VkPipelineStageFlags2 stage_mask; uint64_t signal_value; };
struct pvr_winsys;
struct ops { VkResult (*null_job_submit)(struct pvr_winsys *, struct vk_sync_wait *, uint32_t, struct vk_sync_signal *); };
struct pvr_winsys { struct ops *ops; int syncobj_type; };
struct pdevice { struct pvr_winsys *ws; };
struct pvr_device { struct vk_device vk; struct pdevice *pdevice; struct pvr_winsys *ws; };
struct pvr_queue { struct pvr_device *device; struct vk_sync *last_job_signal_sync[PVR_JOB_TYPE_MAX]; struct vk_sync *next_job_wait_sync[PVR_JOB_TYPE_MAX]; };
static unsigned live_syncs;
static int fail_join;
static VkResult vk_sync_create(struct vk_device *dev, int *type, unsigned flags, unsigned long value, struct vk_sync **out)
{
    *out = calloc(1, sizeof(**out));
    if (!*out) return VK_ERROR_OUT_OF_HOST_MEMORY;
    ++live_syncs;
    return VK_SUCCESS;
}
static void vk_sync_destroy(struct vk_device *dev, struct vk_sync *sync)
{
    --live_syncs;
    free(sync);
}
static enum pvr_pipeline_stage_bits pvr_stage_mask_src(VkPipelineStageFlags2 mask) { return (enum pvr_pipeline_stage_bits)mask; }
static unsigned pvr_stage_mask_dst(VkPipelineStageFlags2 mask) { return (unsigned)mask; }
static VkResult join(struct pvr_winsys *ws, struct vk_sync_wait *waits, uint32_t count, struct vk_sync_signal *signal)
{
    if (fail_join) return VK_ERROR_OUT_OF_HOST_MEMORY;
    signal->sync->dependencies = 0;
    for (uint32_t i = 0; i < count; ++i)
        signal->sync->dependencies |= waits[i].sync->dependencies;
    return VK_SUCCESS; /* Dependencies remain pending; no CPU completion wait. */
}
/* ACTUAL_FUNCTIONS */
int main(void)
{
    struct ops ops = { join };
    struct pvr_winsys ws = { &ops, 0 };
    struct pdevice physical = { &ws };
    struct pvr_device device = { {0}, &physical, &ws };
    struct pvr_queue queue = { .device = &device };
    struct vk_sync first = {1}, second = {2}, third = {4}, output = {0};
    struct vk_sync_wait wait = { &first, BITFIELD_BIT(JOB_FRAG), 0 };
    struct vk_sync_signal signal = { &output, STAGES_ALL, 0 };
    assert(pvr_process_queue_waits(&queue, &wait, 1) == VK_SUCCESS);
    assert(pvr_process_queue_signals(&queue, &signal, 1) == VK_SUCCESS);
    assert(output.dependencies == 1); /* Empty wait-only submit must not signal early. */
    wait.sync = &second;
    assert(pvr_process_queue_waits(&queue, &wait, 1) == VK_SUCCESS);
    assert(queue.next_job_wait_sync[JOB_FRAG]->dependencies == 3);
    assert(live_syncs == 1); /* The replaced userspace object is retired. */
    fail_join = 1;
    wait.sync = &third;
    assert(pvr_process_queue_waits(&queue, &wait, 1) != VK_SUCCESS);
    assert(queue.next_job_wait_sync[JOB_FRAG]->dependencies == 3 && live_syncs == 1);
    fail_join = 0;
    struct vk_sync *job;
    assert(vk_sync_create(&device.vk, &ws.syncobj_type, 0, 0, &job) == VK_SUCCESS);
    job->dependencies = 3; /* Winsys job captured its input dependencies. */
    pvr_update_job_syncs(&device, &queue, job, JOB_FRAG);
    assert(!queue.next_job_wait_sync[JOB_FRAG] && live_syncs == 1);
    wait.stage_mask = BITFIELD_BIT(JOB_TRANSFER);
    assert(pvr_process_queue_waits(&queue, &wait, 1) == VK_SUCCESS);
    assert(pvr_process_queue_signals(&queue, &signal, 1) == VK_SUCCESS);
    assert(output.dependencies == 7); /* Earlier job tail plus pending stage wait. */
    assert(queue.last_job_signal_sync[JOB_FRAG] == job); /* Empty fence keeps tail. */
    for (unsigned i = 0; i < PVR_JOB_TYPE_MAX; ++i) {
        if (queue.next_job_wait_sync[i]) vk_sync_destroy(&device.vk, queue.next_job_wait_sync[i]);
        if (queue.last_job_signal_sync[i]) vk_sync_destroy(&device.vk, queue.last_job_signal_sync[i]);
    }
    assert(!live_syncs);
    puts("PASS: queue tails, wait-only signals, merge ownership, join failure");
    return 0;
}
