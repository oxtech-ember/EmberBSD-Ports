$NetBSD$

Support PowerVR simple parameter format version 1 (GE8300).
Version 1 uses one macrotile for the render and has no 2x2 tile groups.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/vulkan/pvr_arch_job_render.c.orig
+++ src/imagination/vulkan/pvr_arch_job_render.c
@@ -127,7 +127,23 @@
 
    rogue_get_num_macrotiles_xy(dev_info, &info->mtiles_x, &info->mtiles_y);
 
-   if (PVR_HAS_FEATURE(dev_info, simple_internal_parameter_format)) {
+   if (PVR_HAS_FEATURE(dev_info, simple_internal_parameter_format) &&
+       PVR_GET_FEATURE_VALUE(dev_info, simple_parameter_format_version, 0) ==
+          1) {
+      /* Parameter format version 1 has a single macrotile (see
+       * rogue_get_num_macrotiles_xy()). It covers the whole render, and the
+       * tiles have no 2x2 groups.
+       */
+      assert(info->mtiles_x == 1 && info->mtiles_y == 1);
+      info->mtile_x1 = info->num_tiles_x;
+      info->mtile_y1 = info->num_tiles_y;
+      info->mtile_x2 = 0;
+      info->mtile_y2 = 0;
+      info->mtile_x3 = 0;
+      info->mtile_y3 = 0;
+      info->x_tile_max = info->num_tiles_x - 1;
+      info->y_tile_max = info->num_tiles_y - 1;
+   } else if (PVR_HAS_FEATURE(dev_info, simple_internal_parameter_format)) {
       assert(PVR_GET_FEATURE_VALUE(dev_info,
                                    simple_parameter_format_version,
                                    0) == 2);
