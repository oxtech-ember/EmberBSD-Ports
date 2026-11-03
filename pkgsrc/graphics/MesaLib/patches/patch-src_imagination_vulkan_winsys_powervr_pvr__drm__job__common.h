$NetBSD$

PowerVR submit errors can leave a completed prefix.  Do not retry
NetBSD ioctls; terminate the queue when completion is uncertain.
Origin: EmberBSD contributors. SPDX-License-Identifier: MIT.

--- src/imagination/vulkan/winsys/powervr/pvr_drm_job_common.h.orig
+++ src/imagination/vulkan/winsys/powervr/pvr_drm_job_common.h
@@ -24,9 +24,35 @@
 #ifndef PVR_DRM_JOB_COMMON_H
 #define PVR_DRM_JOB_COMMON_H
 
+#include <errno.h>
+#include <string.h>
+#if defined(__NetBSD__)
+#include <sys/ioctl.h>
+#endif
+
 #include "drm-uapi/pvr_drm.h"
 #include "pvr_winsys.h"
+#include "pvr_winsys_helper.h"
 #include "util/macros.h"
+
+/* NetBSD may have executed a prefix when an ioctl fails.  libdrm's
+ * drmIoctl retries EINTR and EAGAIN, which could replay that prefix. */
+static VkResult pvr_drm_submit_jobs(int fd,
+                                    struct drm_pvr_ioctl_submit_jobs_args *args,
+                                    const char *message)
+{
+#if defined(__NetBSD__)
+   if (ioctl(fd, DRM_IOCTL_PVR_SUBMIT_JOBS, args) != 0) {
+      int error = errno;
+      return vk_errorf(NULL, VK_ERROR_DEVICE_LOST,
+                       "%s (errno %d: %s)", message, error, strerror(error));
+   }
+   return VK_SUCCESS;
+#else
+   return pvr_ioctlf(fd, DRM_IOCTL_PVR_SUBMIT_JOBS, args,
+                     VK_ERROR_OUT_OF_DEVICE_MEMORY, "%s", message);
+#endif
+}
 
 static enum drm_pvr_ctx_priority
 pvr_drm_from_winsys_priority(enum pvr_winsys_ctx_priority priority)
