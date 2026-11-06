$NetBSD$

Keep single-sample shaders without discards opaque or translucent.
They need no sample check, alpha to one or ISP feedback. Punch-through
feedback costs several clocks per pixel on GE8300.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/pco/pco_nir_pvfio.c.orig
+++ src/imagination/pco/pco_nir_pvfio.c
@@ -544,6 +544,14 @@
       has_depth_feedback = true;
    }
 
+   /* Single-sample coverage without discards is final: keep the object
+    * opaque or translucent instead of punch-through.
+    */
+   if (!state->fs->meta_present.multisample && !state->has_discards &&
+       !has_depth_feedback) {
+      return false;
+   }
+
    if (!state->has_sample_check) {
       b->cursor = nir_after_instr(&state->last_discard_store->instr);
 
@@ -844,7 +852,7 @@
    /* TODO: instead of doing multiple passes, probably better to just cache all
     * the stores
     */
-   if (!shader->info.internal) {
+   if (!shader->info.internal && fs->meta_present.multisample) {
       progress |= nir_shader_intrinsics_pass(shader,
                                              lower_alpha_to_one,
                                              nir_metadata_control_flow,
