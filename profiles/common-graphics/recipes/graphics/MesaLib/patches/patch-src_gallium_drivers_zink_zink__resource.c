$NetBSD$

Keep the scanout handle alive until the resource import has completed.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.

--- src/gallium/drivers/zink/zink_resource.c.orig
+++ src/gallium/drivers/zink/zink_resource.c
@@ -1837,8 +1837,8 @@
       templ2.bind |= PIPE_BIND_SHADER_IMAGE;
 
 #ifdef HAVE_LIBDRM
+   struct winsys_handle handle;
    if (!whandle && screen->ro && (templ2.bind & PIPE_BIND_SCANOUT)) {
-      struct winsys_handle handle;
 
       assert(screen->info.have_EXT_image_drm_format_modifier);
 
