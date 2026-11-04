$NetBSD$

Encode the PPP terminate clip in tiles on simple parameter format version 1
cores (GE8300). The 32-pixel blocks used by other cores make the tile
accelerator finish only the top-left quarter of the render.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/vulkan/pvr_arch_framebuffer.c.orig
+++ src/imagination/vulkan/pvr_arch_framebuffer.c
@@ -31,8 +31,20 @@
 pvr_render_state_create_ppp_state(struct pvr_device *device,
                                   struct pvr_render_state *rstate)
 {
-   const uint32_t cache_line_size =
-      pvr_get_slc_cache_line_size(&device->pdevice->dev_info);
+   const struct pvr_device_info *dev_info = &device->pdevice->dev_info;
+   const uint32_t cache_line_size = pvr_get_slc_cache_line_size(dev_info);
+   /* Parameter format version 1 cores take the terminate clip in tiles. */
+   const bool clip_in_tiles =
+      PVR_HAS_FEATURE(dev_info, simple_internal_parameter_format) &&
+      PVR_GET_FEATURE_VALUE(dev_info, simple_parameter_format_version, 0) == 1;
+   const uint32_t clip_block_x =
+      clip_in_tiles
+         ? PVR_GET_FEATURE_VALUE(dev_info, tile_size_x, 16U)
+         : ROGUE_TA_STATE_TERMINATE0_CLIP_RIGHT_BLOCK_SIZE_IN_PIXELS;
+   const uint32_t clip_block_y =
+      clip_in_tiles
+         ? PVR_GET_FEATURE_VALUE(dev_info, tile_size_y, 16U)
+         : ROGUE_TA_STATE_TERMINATE0_CLIP_BOTTOM_BLOCK_SIZE_IN_PIXELS;
    uint32_t ppp_state[3];
    VkResult result;
 
@@ -41,16 +53,8 @@
    }
 
    pvr_csb_pack (&ppp_state[1], TA_STATE_TERMINATE0, term0) {
-      term0.clip_right =
-         DIV_ROUND_UP(
-            rstate->width,
-            ROGUE_TA_STATE_TERMINATE0_CLIP_RIGHT_BLOCK_SIZE_IN_PIXELS) -
-         1;
-      term0.clip_bottom =
-         DIV_ROUND_UP(
-            rstate->height,
-            ROGUE_TA_STATE_TERMINATE0_CLIP_BOTTOM_BLOCK_SIZE_IN_PIXELS) -
-         1;
+      term0.clip_right = DIV_ROUND_UP(rstate->width, clip_block_x) - 1;
+      term0.clip_bottom = DIV_ROUND_UP(rstate->height, clip_block_y) - 1;
    }
 
    pvr_csb_pack (&ppp_state[2], TA_STATE_TERMINATE1, term1) {
