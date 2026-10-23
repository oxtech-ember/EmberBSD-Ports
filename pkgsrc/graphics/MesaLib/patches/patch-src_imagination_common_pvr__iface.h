$NetBSD$

Reserve all four sampler words in the shared IDFWDF layout.
Keep compiler input and the Vulkan runtime on the same layout.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
See probes/a733-accelerators/idfwdf for the source-causal ABI checks.

--- src/imagination/common/pvr_iface.h.orig
+++ src/imagination/common/pvr_iface.h
@@ -33,7 +33,7 @@ enum pvr_idfwdf_data {
    PVR_IDFWDF_DATA_TEX = 0,
    PVR_IDFWDF_DATA_SMP = 4,
 
-   PVR_IDFWDF_DATA_ADDR_LO,
+   PVR_IDFWDF_DATA_ADDR_LO = 8,
    PVR_IDFWDF_DATA_ADDR_HI,
 
    _PVR_IDFWDF_DATA_COUNT,
