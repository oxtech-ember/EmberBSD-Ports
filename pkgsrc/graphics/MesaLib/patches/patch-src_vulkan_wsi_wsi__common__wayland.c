$NetBSD$

Use RAW presentation clocks only when the platform defines them.
Keep monotonic presentation timing and the existing unknown-domain fallbacks.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.

--- src/vulkan/wsi/wsi_common_wayland.c.orig
+++ src/vulkan/wsi/wsi_common_wayland.c
@@ -287,8 +287,10 @@
    switch (id) {
       case CLOCK_MONOTONIC:
          return VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR;
+#ifdef CLOCK_MONOTONIC_RAW
       case CLOCK_MONOTONIC_RAW:
          return VK_TIME_DOMAIN_CLOCK_MONOTONIC_RAW_KHR;
+#endif
       default:
          /* Default fallback. Will likely not be used, but is safe to use. */
          return VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR;
@@ -301,8 +303,10 @@
    switch (id) {
       case VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR:
          return CLOCK_MONOTONIC;
+#ifdef CLOCK_MONOTONIC_RAW
       case VK_TIME_DOMAIN_CLOCK_MONOTONIC_RAW_KHR:
          return CLOCK_MONOTONIC_RAW;
+#endif
       default:
          /* Default fallback. Will not be used. */
          return 0;
@@ -2128,7 +2132,11 @@
          /* We could deal with esoteric clock domains by exposing VK_TIME_DOMAIN_SWAPCHAIN or PRESENT_STAGE_LOCAL,
           * but that requires a lot more scaffolding, and there's no need to add extra complexity if we can
           * get away with this. */
-         if (clock_id != CLOCK_MONOTONIC && clock_id != CLOCK_MONOTONIC_RAW)
+         if (clock_id != CLOCK_MONOTONIC
+#ifdef CLOCK_MONOTONIC_RAW
+             && clock_id != CLOCK_MONOTONIC_RAW
+#endif
+            )
             break;
 
          /* Presentation timing spec talks about the reported time targeting "pixel being visible".
