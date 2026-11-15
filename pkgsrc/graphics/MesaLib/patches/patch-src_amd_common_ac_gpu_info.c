Origin: EmberBSD; AI-assisted Mesa 26.2.5 NetBSD DRM 3.36 compatibility,
rebased for Mesa 26.3.0.
Status: local; not submitted upstream.

Keep the upstream DRM 3.59 requirement on other systems. NetBSD's AMDGPU
driver reports DRM 3.36. RadeonSI has compatibility paths for older kernels,
including a no-op submission after reset when reset-in-progress is unavailable.
Mesa 26.3 also drops the has_gpuvm_fault_query and gfx12_supports_display_dcc
DRM gates (debug-only fault query; GFX12 is not supported on NetBSD).
The VA surface clear for older kernels is in the radeonsi si_mm_screen.c patch.

--- src/amd/common/ac_gpu_info.c.orig
+++ src/amd/common/ac_gpu_info.c
@@ -1503,11 +1503,18 @@ ac_query_gpu_info(int fd, void *dev_p, struct radeon_info *info,
    assert(info->drm_major == AC_AMDGPU_DRM_MAJOR);
    info->is_amdgpu = true;
 
+#if defined(__NetBSD__)
+   if (info->drm_minor < 36) {
+      fprintf(stderr, "amdgpu: DRM version is %u.%u.%u, but this driver is "
+                      "only compatible with 3.36.0 or later on NetBSD.\n",
+              info->drm_major, info->drm_minor, info->drm_patchlevel);
+#else
    if (info->drm_minor < AC_AMDGPU_DRM_MINOR) {
       fprintf(stderr, "amdgpu: DRM version is %u.%u.%u, but this driver is "
                       "only compatible with %u.%u.0 (kernel 6.11.2+) or later.\n",
               info->drm_major, info->drm_minor, info->drm_patchlevel,
               AC_AMDGPU_DRM_MAJOR, AC_AMDGPU_DRM_MINOR);
+#endif
       return false;
    }
 
