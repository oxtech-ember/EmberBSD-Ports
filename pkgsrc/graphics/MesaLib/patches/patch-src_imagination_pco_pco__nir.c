$NetBSD$

Lower alpha to coverage only when multisample state can apply.
Mesa 26.3 always inserts a sample check. Single-sample coverage always
contains sample 0, so pass the multisample state to skip that no-op check.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/pco/pco_nir.c.orig
+++ src/imagination/pco/pco_nir.c
@@ -1058,7 +1058,7 @@ void pco_lower_nir(pco_ctx *ctx, nir_shader *nir, pco_data *data)
    NIR_PASS(_, nir, pco_nir_lower_tex, data, ctx);
 
    if (nir->info.stage == MESA_SHADER_FRAGMENT) {
-      if (!internal)
+      if (!internal && data->fs.meta_present.multisample)
          NIR_PASS(_, nir, pco_nir_lower_alpha_to_coverage);
 
       NIR_PASS(_, nir, nir_lower_blend, &data->fs.blend_opts);
@@ -1070,7 +1070,10 @@ void pco_lower_nir(pco_ctx *ctx, nir_shader *nir, pco_data *data)
       NIR_PASS(_, nir, nir_opt_peephole_select, &peep_opts);
       NIR_PASS(_, nir, pco_nir_lower_interpolation, &data->fs);
       if (!internal)
-         NIR_PASS(_, nir, pco_nir_lower_sample_mask_out);
+         NIR_PASS(_,
+                  nir,
+                  pco_nir_lower_sample_mask_out,
+                  data->fs.meta_present.multisample);
       NIR_PASS(_, nir, pco_nir_pfo, &data->fs);
       NIR_PASS(_, nir, nir_lower_is_helper_invocation);
       NIR_PASS(_, nir, pco_nir_lower_fs_intrinsics);
