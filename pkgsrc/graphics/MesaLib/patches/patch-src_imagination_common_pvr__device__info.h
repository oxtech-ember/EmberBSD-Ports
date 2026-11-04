$NetBSD$

Use the device D24 background-depth register capability.
The GE8300 22.102.54.38 table selects floating-point encoding.
Other device tables keep the existing encoding.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.
Not yet submitted upstream.

--- src/imagination/common/pvr_device_info.h.orig
+++ src/imagination/common/pvr_device_info.h
@@ -266,6 +266,7 @@
    bool has_gpu_multicore_support : 1;
    bool has_gs_rta_support : 1;
    bool has_ipf_creq_pf : 1;
+   bool has_isp_bgobjdepth_d24_float : 1;
    bool has_isp_max_tiles_in_flight : 1;
    bool has_isp_samples_per_pixel : 1;
    bool has_max_instances_per_pds_task : 1;
