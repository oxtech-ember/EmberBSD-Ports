$NetBSD$

Keep single-sample shaders without discards opaque or translucent.
They need no sample check, alpha to one or ISP feedback. Punch-through
feedback costs several clocks per pixel on GE8300.
Mesa 26.3 derives the ISP discard from is_helper_invocation; keep it only
when the shader has a discard, a depth feedback source or multisample state.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/pco/pco_internal.h.orig
+++ src/imagination/pco/pco_internal.h
@@ -1828,7 +1828,7 @@ bool pco_nir_lower_vs_intrinsics(nir_shader *shader);
 bool pco_nir_lower_images(nir_shader *shader, pco_data *data, pco_ctx *ctx);
 bool pco_nir_lower_interpolation(nir_shader *shader, pco_fs_data *fs);
 bool pco_nir_lower_io(nir_shader *shader, pco_data *data);
-bool pco_nir_lower_sample_mask_out(nir_shader *shader);
+bool pco_nir_lower_sample_mask_out(nir_shader *shader, bool multisample);
 bool pco_nir_lower_shared_io_to_global(nir_shader *shader, unsigned usc_slots);
 bool pco_nir_lower_subgroups(nir_shader *shader);
 bool pco_nir_lower_tex(nir_shader *shader, pco_data *data, pco_ctx *ctx);
--- src/imagination/pco/pco_nir_pvfio.c.orig
+++ src/imagination/pco/pco_nir_pvfio.c
@@ -499,12 +499,16 @@ static bool lower_sample_mask_out(nir_builder *b, nir_intrinsic_instr *intr, UNU
    return true;
 }
 
-bool pco_nir_lower_sample_mask_out(nir_shader *shader)
+bool pco_nir_lower_sample_mask_out(nir_shader *shader, bool multisample)
 {
    bool progress = nir_shader_intrinsics_pass(shader, lower_sample_mask_out, nir_metadata_control_flow, NULL);
    if (progress)
       return true;
 
+   /* Single-sample coverage always contains sample 0: the check is a no-op. */
+   if (!multisample)
+      return false;
+
    /* If the sample check isn't present, then add one ourselves. */
    nir_builder b = nir_builder_at(
       nir_before_block(nir_start_block(nir_shader_get_entrypoint(shader))));
@@ -514,6 +518,31 @@ bool pco_nir_lower_sample_mask_out(nir_shader *shader)
    return true;
 }
 
+static bool fs_has_discards(nir_shader *shader)
+{
+   nir_foreach_function_impl (impl, shader) {
+      nir_foreach_block (block, impl) {
+         nir_foreach_instr (instr, block) {
+            if (instr->type != nir_instr_type_intrinsic)
+               continue;
+
+            switch (nir_instr_as_intrinsic(instr)->intrinsic) {
+            case nir_intrinsic_demote:
+            case nir_intrinsic_demote_if:
+            case nir_intrinsic_demote_samples:
+            case nir_intrinsic_terminate:
+            case nir_intrinsic_terminate_if:
+               return true;
+            default:
+               break;
+            }
+         }
+      }
+   }
+
+   return false;
+}
+
 static bool lower_isp_fb(nir_builder *b, struct pfo_state *state)
 {
    nir_shader *shader = b->shader;
@@ -541,6 +570,15 @@ static bool lower_isp_fb(nir_builder *b, struct pfo_state *state)
                         });
    }
 
+   /* Single-sample coverage without discards is final: keep the object
+    * opaque or translucent instead of punch-through. ISP feedback costs
+    * several clocks per pixel on GE8300.
+    */
+   if (!state->fs->meta_present.multisample && !state->depth_feedback_src &&
+       !fs_has_discards(shader)) {
+      return false;
+   }
+
    /* Insert isp feedback instruction before the first store,
     * or if there are no stores, at the end.
     */
@@ -814,7 +852,7 @@ bool pco_nir_pfo(nir_shader *shader, pco_fs_data *fs)
    /* TODO: instead of doing multiple passes, probably better to just cache all
     * the stores
     */
-   if (!shader->info.internal) {
+   if (!shader->info.internal && fs->meta_present.multisample) {
       progress |= nir_shader_intrinsics_pass(shader,
                                              lower_alpha_to_one,
                                              nir_metadata_control_flow,
