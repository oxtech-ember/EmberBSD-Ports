$NetBSD$

Keep immutable scalar push constants visible to PCO copy propagation.
Vector and dynamically indexed loads retain their existing lowering.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream; diagnostic candidate pending hardware validation.

--- src/imagination/pco/pco_trans_nir.c.orig
+++ src/imagination/pco/pco_trans_nir.c
@@ -946,6 +946,12 @@
       assert(offset < range->count);
 
       pco_ref src = pco_ref_hwreg_vec(range->start + offset, reg_class, chans);
+      /* Push constants cannot change during shader execution. Keep scalar
+       * copies visible to propagation; legalization handles source banks.
+       */
+      if (intr->intrinsic == nir_intrinsic_load_push_constant && chans == 1)
+         return pco_mov(&tctx->b, dest, src);
+
       return pco_mbyp(&tctx->b, dest, src, .rpt = chans);
    }
 
