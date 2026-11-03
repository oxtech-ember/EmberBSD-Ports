$NetBSD$

PowerVR submit errors can leave a completed prefix.  Do not retry
NetBSD ioctls; terminate the queue when completion is uncertain.
Origin: EmberBSD contributors. SPDX-License-Identifier: MIT.

--- src/imagination/vulkan/winsys/powervr/pvr_drm_job_compute.c.orig
+++ src/imagination/vulkan/winsys/powervr/pvr_drm_job_compute.c
@@ -214,10 +214,5 @@
       };
    }
 
-   /* Returns VK_ERROR_OUT_OF_DEVICE_MEMORY to match pvrsrv. */
-   return pvr_ioctlf(drm_ws->base.render_fd,
-                     DRM_IOCTL_PVR_SUBMIT_JOBS,
-                     &args,
-                     VK_ERROR_OUT_OF_DEVICE_MEMORY,
-                     "Failed to submit compute job");
-}
+   return pvr_drm_submit_jobs(drm_ws->base.render_fd, &args, "Failed to submit compute job");
+}
