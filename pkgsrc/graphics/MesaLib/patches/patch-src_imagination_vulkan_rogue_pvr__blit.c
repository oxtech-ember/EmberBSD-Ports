$NetBSD$

Keep aligned odd one-row SIPFv1 transfers on the normal GPU TQ path.
FAST_2D can reset these contexts. Split off the final texel instead.
Preserve unaligned and byte-sized transfer handling.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/vulkan/rogue/pvr_blit.c.orig
+++ src/imagination/vulkan/rogue/pvr_blit.c
@@ -1460,6 +1460,18 @@
          height = 1;
       }
 
+      /* Keep aligned one-row transfers on the normal GPU TQ path.
+       * Odd PBE strides select FAST_2D, which can reset SIPFv1 contexts.
+       * The next iteration handles the remaining texel.
+       */
+      if (PVR_HAS_FEATURE(&cmd_buffer->device->pdevice->dev_info,
+                          simple_internal_parameter_format_v1) &&
+          height == 1 && width > 1 && (width & 1U) && texel_width >= 4 &&
+          (is_fill || (src_align & 3U) == 0) &&
+          ((dst_addr.addr + offset + dst_offset) & 3U) == 0) {
+         width--;
+      }
+
       transfer_cmd = pvr_transfer_cmd_alloc(cmd_buffer);
       if (!transfer_cmd)
          return VK_ERROR_OUT_OF_HOST_MEMORY;
