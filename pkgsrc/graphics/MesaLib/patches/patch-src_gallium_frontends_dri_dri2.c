$NetBSD$

A failed BO allocation can leave a DRI image without a backing
resource; the image attribute queries must reject such images instead
of dereferencing the NULL texture. Crashes observed as plasmashell
SIGSEGV in dri2_query_image during eglSwapBuffers on V3D.

--- src/gallium/frontends/dri/dri2.c.orig	2026-10-14
+++ src/gallium/frontends/dri/dri2.c
@@ -995,9 +995,13 @@
 {
    switch (attrib) {
    case __DRI_IMAGE_ATTRIB_WIDTH:
+      if (!image->texture)
+         return false;
       *value = image->texture->width0;
       return true;
    case __DRI_IMAGE_ATTRIB_HEIGHT:
+      if (!image->texture)
+         return false;
       *value = image->texture->height0;
       return true;
    case __DRI_IMAGE_ATTRIB_FOURCC:
@@ -1028,7 +1032,12 @@
 static bool
 dri2_query_image_by_resource_handle(struct dri_image *image, int attrib, int *value)
 {
-   struct pipe_screen *pscreen = image->texture->screen;
+   struct pipe_screen *pscreen;
+
+   if (!image->texture)
+      return false;
+
+   pscreen = image->texture->screen;
    struct winsys_handle whandle;
    struct pipe_resource *tex;
    unsigned usage;
@@ -1131,6 +1140,9 @@
    uint64_t res_param;
    unsigned handle_usage;
 
+   if (!image->texture)
+      return false;
+
    if (!image->texture->screen->resource_get_param)
       return false;
 
