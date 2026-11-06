$NetBSD$

Keep PowerVR queue dependencies across submissions without a CPU drain.
Merge pending waits and include them in wait-only submission signals.
Preserve NetBSD queue-loss handling after uncertain ioctl completion.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.

--- src/imagination/vulkan/pvr_arch_queue.c.orig
+++ src/imagination/vulkan/pvr_arch_queue.c
@@ -869,59 +869,11 @@
    return VK_SUCCESS;
 }
 
-static VkResult pvr_clear_last_submits_syncs(struct pvr_queue *queue)
-{
-   struct vk_sync_wait waits[PVR_JOB_TYPE_MAX * 2];
-   uint32_t wait_count = 0;
-   VkResult result;
-
-   for (uint32_t i = 0; i < PVR_JOB_TYPE_MAX; i++) {
-      if (queue->next_job_wait_sync[i]) {
-         waits[wait_count++] = (struct vk_sync_wait){
-            .sync = queue->next_job_wait_sync[i],
-            .stage_mask = ~(VkPipelineStageFlags2)0,
-            .wait_value = 0,
-         };
-      }
-
-      if (queue->last_job_signal_sync[i]) {
-         waits[wait_count++] = (struct vk_sync_wait){
-            .sync = queue->last_job_signal_sync[i],
-            .stage_mask = ~(VkPipelineStageFlags2)0,
-            .wait_value = 0,
-         };
-      }
-   }
-
-   result = vk_sync_wait_many(&queue->device->vk,
-                              wait_count,
-                              waits,
-                              VK_SYNC_WAIT_COMPLETE,
-                              UINT64_MAX);
-
-   if (result != VK_SUCCESS)
-      return vk_error(queue, result);
-
-   for (uint32_t i = 0; i < PVR_JOB_TYPE_MAX; i++) {
-      if (queue->next_job_wait_sync[i]) {
-         vk_sync_destroy(&queue->device->vk, queue->next_job_wait_sync[i]);
-         queue->next_job_wait_sync[i] = NULL;
-      }
-
-      if (queue->last_job_signal_sync[i]) {
-         vk_sync_destroy(&queue->device->vk, queue->last_job_signal_sync[i]);
-         queue->last_job_signal_sync[i] = NULL;
-      }
-   }
-
-   return VK_SUCCESS;
-}
-
 static VkResult pvr_process_queue_signals(struct pvr_queue *queue,
                                           struct vk_sync_signal *signals,
                                           uint32_t signal_count)
 {
-   struct vk_sync_wait signal_waits[PVR_JOB_TYPE_MAX];
+   struct vk_sync_wait signal_waits[PVR_JOB_TYPE_MAX * 2];
    struct pvr_device *device = queue->device;
    VkResult result;
 
@@ -938,14 +890,22 @@
          if (!(signal_stage_src & BITFIELD_BIT(i)) && i != PVR_JOB_TYPE_QUERY)
             continue;
 
-         if (!queue->last_job_signal_sync[i])
-            continue;
-
-         signal_waits[wait_count++] = (struct vk_sync_wait){
-            .sync = queue->last_job_signal_sync[i],
-            .stage_mask = ~(VkPipelineStageFlags2)0,
-            .wait_value = 0,
-         };
+         if (queue->last_job_signal_sync[i]) {
+            signal_waits[wait_count++] = (struct vk_sync_wait){
+               .sync = queue->last_job_signal_sync[i],
+               .stage_mask = ~(VkPipelineStageFlags2)0,
+               .wait_value = 0,
+            };
+         }
+
+         /* A wait-only submission must also delay its signals. */
+         if (queue->next_job_wait_sync[i]) {
+            signal_waits[wait_count++] = (struct vk_sync_wait){
+               .sync = queue->next_job_wait_sync[i],
+               .stage_mask = ~(VkPipelineStageFlags2)0,
+               .wait_value = 0,
+            };
+         }
       }
 
       result = device->ws->ops->null_job_submit(device->ws,
@@ -966,12 +926,16 @@
    struct pvr_device *device = queue->device;
    VkResult result;
 
-   STACK_ARRAY(struct vk_sync_wait, stage_waits, wait_count);
+   if (wait_count == UINT32_MAX)
+      return vk_error(queue, VK_ERROR_OUT_OF_HOST_MEMORY);
+
+   STACK_ARRAY(struct vk_sync_wait, stage_waits, wait_count + 1);
    if (!stage_waits)
       return vk_error(queue, VK_ERROR_OUT_OF_HOST_MEMORY);
 
    for (uint32_t i = 0; i < PVR_JOB_TYPE_MAX; i++) {
       struct vk_sync_signal next_job_wait_signal_sync;
+      struct vk_sync *next_wait_sync;
       uint32_t stage_wait_count = 0;
 
       for (uint32_t wait_idx = 0; wait_idx < wait_count; wait_idx++) {
@@ -990,16 +954,25 @@
       if (!stage_wait_count)
          continue;
 
+      /* Keep dependencies from prior submits until a job consumes them. */
+      if (queue->next_job_wait_sync[i]) {
+         stage_waits[stage_wait_count++] = (struct vk_sync_wait){
+            .sync = queue->next_job_wait_sync[i],
+            .stage_mask = ~(VkPipelineStageFlags2)0,
+            .wait_value = 0,
+         };
+      }
+
       result = vk_sync_create(&device->vk,
                               &device->pdevice->ws->syncobj_type,
                               0U,
                               0UL,
-                              &queue->next_job_wait_sync[i]);
+                              &next_wait_sync);
       if (result != VK_SUCCESS)
          goto err_free_waits;
 
       next_job_wait_signal_sync = (struct vk_sync_signal){
-         .sync = queue->next_job_wait_sync[i],
+         .sync = next_wait_sync,
          .stage_mask = ~(VkPipelineStageFlags2)0,
          .signal_value = 0,
       };
@@ -1008,8 +981,14 @@
                                                 stage_waits,
                                                 stage_wait_count,
                                                 &next_job_wait_signal_sync);
-      if (result != VK_SUCCESS)
+      if (result != VK_SUCCESS) {
+         vk_sync_destroy(&device->vk, next_wait_sync);
          goto err_free_waits;
+      }
+
+      if (queue->next_job_wait_sync[i])
+         vk_sync_destroy(&device->vk, queue->next_job_wait_sync[i]);
+      queue->next_job_wait_sync[i] = next_wait_sync;
    }
 
    STACK_ARRAY_FINISH(stage_waits);
@@ -1029,16 +1008,18 @@
    struct pvr_device *device = driver_queue->device;
    VkResult result;
 
-   result = pvr_clear_last_submits_syncs(driver_queue);
-   if (result != VK_SUCCESS)
-      return result;
+   /* Keep per-stage tails across submissions. Contexts execute jobs in order,
+    * and winsys submissions retain their input fences before returning. Clearing
+    * these tails here would either wait on the CPU or lose cross-submit barriers
+    * and the dependency of an empty fence submission on earlier work.
+    */
 
    if (submit->wait_count) {
       result = pvr_process_queue_waits(driver_queue,
                                        submit->waits,
                                        submit->wait_count);
       if (result != VK_SUCCESS)
-         return result;
+         goto err_submit;
    }
 
    struct pvr_suspended_data suspended_data = {0};
@@ -1050,7 +1031,7 @@
          container_of(submit->command_buffers[i], struct pvr_cmd_buffer, vk),
          &suspended_data);
       if (result != VK_SUCCESS)
-         return result;
+         goto err_submit;
    }
 
    assert(suspended_data.rts == NULL && "suspended graphics job never resumed");
@@ -1059,9 +1040,17 @@
                                       submit->signals,
                                       submit->signal_count);
    if (result != VK_SUCCESS)
-      return result;
-
-   return VK_SUCCESS;
+      goto err_submit;
+
+   return VK_SUCCESS;
+
+err_submit:
+#if defined(__NetBSD__)
+   /* No reliable completed-prefix count is copied out on ioctl error. */
+   return vk_queue_set_lost(queue, "PowerVR queue submission failed");
+#else
+   return result;
+#endif
 }
 
 VkResult PVR_PER_ARCH(QueueBindSparse)(VkQueue _queue,
