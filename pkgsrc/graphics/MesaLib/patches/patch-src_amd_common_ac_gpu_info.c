Origin: EmberBSD; AI-assisted Mesa 26.2.5 NetBSD DRM 3.36 compatibility,
rebased for Mesa 26.3.0.
Status: local; not submitted upstream.

Keep the upstream DRM 3.59 requirement on other systems. NetBSD's AMDGPU
driver reports DRM 3.36. RadeonSI has compatibility paths for older kernels,
including a no-op submission after reset when reset-in-progress is unavailable.
Mesa 26.3 assumes that new VRAM is zeroed (DRM 3.59). Keep clearing new VA
surfaces on older kernels so they never expose stale VRAM contents.

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
 
--- src/gallium/drivers/radeonsi/mm/si_mm_screen.c.orig
+++ src/gallium/drivers/radeonsi/mm/si_mm_screen.c
@@ -38,7 +38,8 @@ static int si_video_get_param(struct pipe_screen *screen, enum pipe_video_profil
       return 1;
 
    case PIPE_VIDEO_CAP_SKIP_CLEAR_SURFACE:
-      return 1;
+      /* Kernels before DRM 3.59 do not zero new VRAM by default. */
+      return sscreen->info.drm_minor >= 59;
 
    default:
       break;
