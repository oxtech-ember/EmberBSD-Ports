$NetBSD$

Support PowerVR simple parameter format version 1 (GE8300).
Version 1 uses one macrotile for the render and has no 2x2 tile groups.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/include/hwdef/rogue_hw_utils.h.orig
+++ src/imagination/include/hwdef/rogue_hw_utils.h
@@ -154,10 +154,12 @@
    *x_out = DIV_ROUND_UP(width * scale_x, tile_samples_x);
    *y_out = DIV_ROUND_UP(height * scale_y, tile_samples_y);
 
-   if (PVR_HAS_FEATURE(dev_info, simple_internal_parameter_format)) {
-      assert(PVR_GET_FEATURE_VALUE(dev_info,
-                                   simple_parameter_format_version,
-                                   0U) == 2U);
+   /* Parameter format version 2 groups tiles in 2x2 blocks; version 1 has
+    * no tile groups.
+    */
+   if (PVR_HAS_FEATURE(dev_info, simple_internal_parameter_format) &&
+       PVR_GET_FEATURE_VALUE(dev_info, simple_parameter_format_version, 0U) ==
+          2U) {
       /* Align to a 2x2 tile block. */
       *x_out = ALIGN_POT(*x_out, 2);
       *y_out = ALIGN_POT(*y_out, 2);
