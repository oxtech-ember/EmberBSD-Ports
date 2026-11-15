Origin: EmberBSD; AI-assisted Mesa 26.3.0 NetBSD DRM 3.36 compatibility.
Status: local; not submitted upstream.

Mesa 26.3 assumes that new VRAM is zeroed (DRM 3.59) and removed
has_default_zerovram_support. NetBSD's AMDGPU driver reports DRM 3.36.
Keep clearing new VA surfaces on older kernels so they never expose stale
VRAM contents.

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
