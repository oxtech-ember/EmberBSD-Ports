$NetBSD$

Use the existing DRM platform types and portable 64-bit flag constants.
Preserve PowerVR structure layout, flag values and ioctl definitions.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.

--- include/drm-uapi/pvr_drm.h.orig
+++ include/drm-uapi/pvr_drm.h
@@ -6,9 +6,6 @@
 
 #include "drm.h"
 
-#include <linux/const.h>
-#include <linux/types.h>
-
 #if defined(__cplusplus)
 extern "C" {
 #endif
@@ -533,9 +530,9 @@
  *    :DRM_PVR_BO_ALLOW_CPU_USERSPACE_ACCESS: Allow userspace to map and access the contents of this
  *       memory. It is not valid to specify this flag with DRM_PVR_BO_PM_FW_PROTECT.
  */
-#define DRM_PVR_BO_BYPASS_DEVICE_CACHE _BITULL(0)
-#define DRM_PVR_BO_PM_FW_PROTECT _BITULL(1)
-#define DRM_PVR_BO_ALLOW_CPU_USERSPACE_ACCESS _BITULL(2)
+#define DRM_PVR_BO_BYPASS_DEVICE_CACHE (1ULL << 0)
+#define DRM_PVR_BO_PM_FW_PROTECT (1ULL << 1)
+#define DRM_PVR_BO_ALLOW_CPU_USERSPACE_ACCESS (1ULL << 2)
 /* Bits 3..63 are reserved. */
 
 #define DRM_PVR_BO_FLAGS_MASK (DRM_PVR_BO_BYPASS_DEVICE_CACHE | DRM_PVR_BO_PM_FW_PROTECT | \
@@ -1056,7 +1053,7 @@
 #define DRM_PVR_SYNC_OP_FLAG_HANDLE_TYPE_MASK 0xf
 #define DRM_PVR_SYNC_OP_FLAG_HANDLE_TYPE_SYNCOBJ 0
 #define DRM_PVR_SYNC_OP_FLAG_HANDLE_TYPE_TIMELINE_SYNCOBJ 1
-#define DRM_PVR_SYNC_OP_FLAG_SIGNAL _BITULL(31)
+#define DRM_PVR_SYNC_OP_FLAG_SIGNAL (1ULL << 31)
 #define DRM_PVR_SYNC_OP_FLAG_WAIT 0
 
 #define DRM_PVR_SYNC_OP_FLAGS_MASK (DRM_PVR_SYNC_OP_FLAG_HANDLE_TYPE_MASK | \
@@ -1095,9 +1092,9 @@
  *
  *    Logical OR of all the geometry cmd flags.
  */
-#define DRM_PVR_SUBMIT_JOB_GEOM_CMD_FIRST _BITULL(0)
-#define DRM_PVR_SUBMIT_JOB_GEOM_CMD_LAST _BITULL(1)
-#define DRM_PVR_SUBMIT_JOB_GEOM_CMD_SINGLE_CORE _BITULL(2)
+#define DRM_PVR_SUBMIT_JOB_GEOM_CMD_FIRST (1ULL << 0)
+#define DRM_PVR_SUBMIT_JOB_GEOM_CMD_LAST (1ULL << 1)
+#define DRM_PVR_SUBMIT_JOB_GEOM_CMD_SINGLE_CORE (1ULL << 2)
 #define DRM_PVR_SUBMIT_JOB_GEOM_CMD_FLAGS_MASK                                 \
 	(DRM_PVR_SUBMIT_JOB_GEOM_CMD_FIRST |                                   \
 	 DRM_PVR_SUBMIT_JOB_GEOM_CMD_LAST |                                    \
@@ -1140,14 +1137,14 @@
  *
  *    Logical OR of all the fragment cmd flags.
  */
-#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_SINGLE_CORE _BITULL(0)
-#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_DEPTHBUFFER _BITULL(1)
-#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_STENCILBUFFER _BITULL(2)
-#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_PREVENT_CDM_OVERLAP _BITULL(3)
-#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_SCRATCHBUFFER _BITULL(4)
-#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_GET_VIS_RESULTS _BITULL(5)
-#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_PARTIAL_RENDER _BITULL(6)
-#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_DISABLE_PIXELMERGE _BITULL(7)
+#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_SINGLE_CORE (1ULL << 0)
+#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_DEPTHBUFFER (1ULL << 1)
+#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_STENCILBUFFER (1ULL << 2)
+#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_PREVENT_CDM_OVERLAP (1ULL << 3)
+#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_SCRATCHBUFFER (1ULL << 4)
+#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_GET_VIS_RESULTS (1ULL << 5)
+#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_PARTIAL_RENDER (1ULL << 6)
+#define DRM_PVR_SUBMIT_JOB_FRAG_CMD_DISABLE_PIXELMERGE (1ULL << 7)
 #define DRM_PVR_SUBMIT_JOB_FRAG_CMD_FLAGS_MASK                                 \
 	(DRM_PVR_SUBMIT_JOB_FRAG_CMD_SINGLE_CORE |                             \
 	 DRM_PVR_SUBMIT_JOB_FRAG_CMD_DEPTHBUFFER |                             \
@@ -1173,8 +1170,8 @@
  *
  *    Logical OR of all the compute cmd flags.
  */
-#define DRM_PVR_SUBMIT_JOB_COMPUTE_CMD_PREVENT_ALL_OVERLAP _BITULL(0)
-#define DRM_PVR_SUBMIT_JOB_COMPUTE_CMD_SINGLE_CORE _BITULL(1)
+#define DRM_PVR_SUBMIT_JOB_COMPUTE_CMD_PREVENT_ALL_OVERLAP (1ULL << 0)
+#define DRM_PVR_SUBMIT_JOB_COMPUTE_CMD_SINGLE_CORE (1ULL << 1)
 #define DRM_PVR_SUBMIT_JOB_COMPUTE_CMD_FLAGS_MASK         \
 	(DRM_PVR_SUBMIT_JOB_COMPUTE_CMD_PREVENT_ALL_OVERLAP | \
 	 DRM_PVR_SUBMIT_JOB_COMPUTE_CMD_SINGLE_CORE)
@@ -1190,7 +1187,7 @@
  *
  *    Logical OR of all the transfer cmd flags.
  */
-#define DRM_PVR_SUBMIT_JOB_TRANSFER_CMD_SINGLE_CORE _BITULL(0)
+#define DRM_PVR_SUBMIT_JOB_TRANSFER_CMD_SINGLE_CORE (1ULL << 0)
 
 #define DRM_PVR_SUBMIT_JOB_TRANSFER_CMD_FLAGS_MASK \
 	DRM_PVR_SUBMIT_JOB_TRANSFER_CMD_SINGLE_CORE
