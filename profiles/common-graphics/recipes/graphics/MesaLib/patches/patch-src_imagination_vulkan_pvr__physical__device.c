$NetBSD$

Use Mesa's existing device-number header checks on BSD.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.

--- src/imagination/vulkan/pvr_physical_device.c.orig
+++ src/imagination/vulkan/pvr_physical_device.c
@@ -12,7 +12,13 @@
 
 #include "pvr_physical_device.h"
 
+#include <sys/types.h>
+#ifdef MAJOR_IN_MKDEV
+#include <sys/mkdev.h>
+#endif
+#ifdef MAJOR_IN_SYSMACROS
 #include <sys/sysmacros.h>
+#endif
 
 #include "git_sha1.h"
 
