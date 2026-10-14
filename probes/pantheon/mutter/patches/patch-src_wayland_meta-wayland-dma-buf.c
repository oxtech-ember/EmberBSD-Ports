$NetBSD$

Local definitions of the Linux dma-buf UAPI on systems without
<linux/dma-buf.h>; includes the export_sync_file ioctl used by the
Wayland dma-buf sync point export. Also keep the linux-drm-syncobj
integration Linux-only. Origin: EmberBSD (AI-assisted).

--- meta-wayland-dma-buf.c	2026-10-14 11:41:25.140417921 +0300
+++ src/wayland/meta-wayland-dma-buf.c	2026-10-14 11:49:43.288402155 +0300
@@ -89,7 +89,9 @@
 #include "wayland/meta-wayland-buffer.h"
 #include "wayland/meta-wayland-private.h"
 #include "wayland/meta-wayland-versions.h"
+#ifdef __linux__
 #include "wayland/meta-wayland-linux-drm-syncobj.h"
+#endif
 
 #ifdef HAVE_NATIVE_BACKEND
 #include "backends/native/meta-drm-buffer-gbm.h"
@@ -1168,6 +1170,7 @@
   return &source->base;
 }
 
+#ifdef __linux__
 GSource *
 meta_wayland_drm_syncobj_create_source (MetaWaylandBuffer                *buffer,
                                         MetaWaylandSyncobjTimeline       *timeline,
@@ -1200,6 +1203,7 @@
 
   return &source->base;
 }
+#endif
 
 static void
 buffer_params_create_common (struct wl_client   *client,
