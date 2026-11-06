$NetBSD$

Drop unused whole-source suffixes from collated PCO vectors. This avoids
materializing the unused padding of texture sample data. Preserve source
widths for register allocation and do not treat collated sources as scalar
component arrays in the following optimization.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream; diagnostic candidate pending hardware validation.

--- src/imagination/pco/pco_opt.c.orig
+++ src/imagination/pco/pco_opt.c
@@ -704,10 +704,6 @@
          if (vec->op != PCO_OP_VEC)
             continue;
 
-         /* Can't shrink if has collated elems. */
-         if (!only_uncollated_elems(vec))
-            continue;
-
          pco_ref *pdest = &vec->dest[0];
          unsigned chans_used = 0;
          unsigned chans = pco_ref_get_chans(*pdest);
@@ -740,8 +736,18 @@
          if (chans_used == chans)
             continue;
 
+         /* Keep complete sources: RA coalesces an SSA producer at its
+          * original width, even when a use references a narrower prefix.
+          */
+         unsigned prefix_chans = 0;
+         unsigned prefix_srcs = 0;
+         while (prefix_srcs < vec->num_srcs && prefix_chans < chans_used)
+            prefix_chans += pco_ref_get_chans(vec->src[prefix_srcs++]);
+         if (prefix_chans != chans_used)
+            continue;
+
          /* Update the vec. */
-         vec->num_srcs = chans_used;
+         vec->num_srcs = prefix_srcs;
          *pdest = pco_ref_chans(*pdest, chans_used);
 
          progress = true;
@@ -792,7 +798,8 @@
 
          /* Has collated vec, skip. */
          /* TODO: support this. */
-         if (vec->num_srcs != util_dynarray_num_elements(&comps, pco_instr *)) {
+         if (!only_uncollated_elems(vec) ||
+             vec->num_srcs != util_dynarray_num_elements(&comps, pco_instr *)) {
             util_dynarray_fini(&comps);
             continue;
          }
