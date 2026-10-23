Origin: EmberBSD; AI-assisted allocation failure repair, not submitted upstream.

Return through the existing unlock path if an imported BO wrapper cannot be
allocated. The actual-source OOM regression exercises this before any ioctl.

--- src/gallium/drivers/v3d/v3d_bufmgr.c.orig
+++ src/gallium/drivers/v3d/v3d_bufmgr.c
@@ -338,6 +338,8 @@
         }
 
         bo = CALLOC_STRUCT(v3d_bo);
+        if (!bo)
+                goto done;
         pipe_reference_init(&bo->reference, 1);
         bo->screen = screen;
         bo->handle = handle;
