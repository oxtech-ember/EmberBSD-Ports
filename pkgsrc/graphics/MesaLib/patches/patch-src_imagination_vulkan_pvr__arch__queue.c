$NetBSD$

PowerVR submit errors can leave a completed prefix.  Do not retry
NetBSD ioctls; terminate the queue when completion is uncertain.
Origin: EmberBSD contributors. SPDX-License-Identifier: MIT.

--- src/imagination/vulkan/pvr_arch_queue.c.orig
+++ src/imagination/vulkan/pvr_arch_queue.c
@@ -1030,6 +1030,8 @@
    VkResult result;
 
    result = pvr_clear_last_submits_syncs(driver_queue);
+   if (result == VK_ERROR_DEVICE_LOST)
+      goto err_submit;
    if (result != VK_SUCCESS)
       return result;
 
@@ -1038,7 +1040,7 @@
                                        submit->waits,
                                        submit->wait_count);
       if (result != VK_SUCCESS)
-         return result;
+         goto err_submit;
    }
 
    struct pvr_suspended_data suspended_data = {0};
@@ -1050,7 +1052,7 @@
          container_of(submit->command_buffers[i], struct pvr_cmd_buffer, vk),
          &suspended_data);
       if (result != VK_SUCCESS)
-         return result;
+         goto err_submit;
    }
 
    assert(suspended_data.rts == NULL && "suspended graphics job never resumed");
@@ -1059,9 +1061,17 @@
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
