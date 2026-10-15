$NetBSD$

Origin: EmberBSD (AI-assisted). Do not cache a failed Wayland back buffer.
get_back_bo selects a slot before allocating its images. Clear its alias on
failure so later callbacks retry allocation and report EGL_BAD_ALLOC.
The slot and its partial resources remain owned by the surface.

--- src/egl/drivers/dri2/platform_wayland.c.orig
+++ src/egl/drivers/dri2/platform_wayland.c
@@ -1527,6 +1527,8 @@
    }
 
    if (get_back_bo(dri2_surf, flow) < 0) {
+      /* A selected slot is not a valid back buffer until allocation succeeds. */
+      dri2_surf->back = NULL;
       _eglError(EGL_BAD_ALLOC, "failed to allocate color buffer");
       return -1;
    }
