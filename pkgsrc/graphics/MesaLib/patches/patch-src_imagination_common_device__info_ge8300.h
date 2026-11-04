$NetBSD$

Use the device D24 background-depth register capability.
The GE8300 22.102.54.38 table selects floating-point encoding.
Other device tables keep the existing encoding.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/common/device_info/ge8300.h.orig
+++ src/imagination/common/device_info/ge8300.h
@@ -145,6 +145,8 @@
    .has_compute_overlap = true,
    /* .has_gs_rta_support = true, */
    .has_ipf_creq_pf = true,
+   /* D24 background depth uses the floating-point register encoding. */
+   .has_isp_bgobjdepth_d24_float = true,
    .has_isp_max_tiles_in_flight = true,
    .has_isp_samples_per_pixel = true,
    .has_max_instances_per_pds_task = true,
