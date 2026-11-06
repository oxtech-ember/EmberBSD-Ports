$NetBSD$

Mark multisample state from static or dynamic pipeline state.
Dynamic, multi-sample, partial-mask and alpha-coverage pipelines keep
the existing lowering.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/vulkan/pvr_arch_pipeline.c.orig
+++ src/imagination/vulkan/pvr_arch_pipeline.c
@@ -2702,6 +2702,20 @@
       if (state->ms)
          data->fs.uses.alpha_to_coverage = state->ms->alpha_to_coverage_enable;
 
+      if (!state->ms ||
+          BITSET_TEST(state->dynamic, MESA_VK_DYNAMIC_MS_RASTERIZATION_SAMPLES) ||
+          BITSET_TEST(state->dynamic, MESA_VK_DYNAMIC_MS_SAMPLE_MASK) ||
+          BITSET_TEST(state->dynamic,
+                      MESA_VK_DYNAMIC_MS_ALPHA_TO_COVERAGE_ENABLE) ||
+          BITSET_TEST(state->dynamic, MESA_VK_DYNAMIC_MS_ALPHA_TO_ONE_ENABLE) ||
+          state->ms->rasterization_samples > VK_SAMPLE_COUNT_1_BIT ||
+          state->ms->sample_shading_enable ||
+          !(state->ms->sample_mask & 1) ||
+          state->ms->alpha_to_coverage_enable ||
+          state->ms->alpha_to_one_enable) {
+         data->fs.meta_present.multisample = true;
+      }
+
       if (BITSET_TEST(state->dynamic, MESA_VK_DYNAMIC_CB_COLOR_WRITE_ENABLES) ||
           (state->cb && state->cb->color_write_enables !=
                            BITFIELD_MASK(MESA_VK_MAX_COLOR_ATTACHMENTS))) {
