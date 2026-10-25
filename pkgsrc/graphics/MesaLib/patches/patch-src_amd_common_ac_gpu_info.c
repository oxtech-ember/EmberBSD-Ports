Origin: EmberBSD; AI-assisted Mesa 26.2.5 NetBSD DRM 3.36 compatibility.
Status: local; not submitted upstream.

Keep the upstream DRM 3.54 requirement on other systems. NetBSD's AMDGPU
driver reports DRM 3.36. RadeonSI has compatibility paths for older kernels,
including a no-op submission after reset when reset-in-progress is unavailable.

--- src/amd/common/ac_gpu_info.c.orig
+++ src/amd/common/ac_gpu_info.c
@@ -1468,10 +1468,17 @@
    assert(info->drm_major == 3);
    info->is_amdgpu = true;
 
+#if defined(__NetBSD__)
+   if (info->drm_minor < 36) {
+      fprintf(stderr, "amdgpu: DRM version is %u.%u.%u, but this driver is "
+                      "only compatible with 3.36.0 or later on NetBSD.\n",
+              info->drm_major, info->drm_minor, info->drm_patchlevel);
+#else
    if (info->drm_minor < 54) {
       fprintf(stderr, "amdgpu: DRM version is %u.%u.%u, but this driver is "
                       "only compatible with 3.54.0 (kernel 6.6+) or later.\n",
               info->drm_major, info->drm_minor, info->drm_patchlevel);
+#endif
       return AC_QUERY_GPU_INFO_FAIL;
    }
 
