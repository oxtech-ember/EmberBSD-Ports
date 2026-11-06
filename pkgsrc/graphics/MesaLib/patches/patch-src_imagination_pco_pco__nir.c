$NetBSD$

Lower alpha to coverage only when multisample state can apply.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/pco/pco_nir.c.orig
+++ src/imagination/pco/pco_nir.c
@@ -991,7 +991,7 @@
 
    if (nir->info.stage == MESA_SHADER_FRAGMENT) {
 
-      if (!internal)
+      if (!internal && data->fs.meta_present.multisample)
          NIR_PASS(_, nir, pco_nir_lower_alpha_to_coverage);
 
       NIR_PASS(_, nir, nir_lower_blend, &data->fs.blend_opts);
