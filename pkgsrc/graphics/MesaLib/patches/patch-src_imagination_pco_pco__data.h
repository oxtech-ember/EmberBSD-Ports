$NetBSD$

Record whether multisample state can change fragment coverage.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/pco/pco_data.h.orig
+++ src/imagination/pco/pco_data.h
@@ -125,6 +125,11 @@
 
    struct {
       bool color_write_enable;
+      /** Whether multisample state (alpha to coverage/one, sample mask or a
+       * sample count above one) can affect coverage. Without it the shader
+       * needs no coverage lowering and no ISP feedback.
+       */
+      bool multisample;
    } meta_present;
 } pco_fs_data;
 
