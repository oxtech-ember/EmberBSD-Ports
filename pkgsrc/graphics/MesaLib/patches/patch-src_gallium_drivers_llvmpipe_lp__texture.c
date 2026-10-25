Origin: EmberBSD; AI-assisted Mesa 26.2.5 POSIX PRIME import repair.
Status: local; not submitted upstream.

Use the existing POSIX DMA-BUF mapping and release path without requiring
Linux UDMABUF allocation. Keep Linux allocation and export guards unchanged.
Release the imported mapping if displaytarget creation fails.
Original Mesa licenses and authorship remain unchanged.

--- src/gallium/drivers/llvmpipe/lp_texture.c.orig
+++ src/gallium/drivers/llvmpipe/lp_texture.c
@@ -47,6 +47,7 @@
 #include "util/u_transfer.h"
 
 #if DETECT_OS_POSIX
+#include <unistd.h>
 #include "util/os_mman.h"
 #endif
 
@@ -604,7 +605,7 @@
       }
    }
 
-#if defined(HAVE_LIBDRM) && defined(HAVE_LINUX_UDMABUF_H)
+#if defined(HAVE_LIBDRM) && DETECT_OS_POSIX
    if (lpr->dmabuf_alloc)
       pscreen->free_memory_fd(pscreen, (struct pipe_memory_allocation*)lpr->dmabuf_alloc);
 #endif
@@ -772,7 +773,7 @@
    lpr->size_required = lpr->sample_stride;
 
    if (whandle->type != WINSYS_HANDLE_TYPE_UNBACKED) {
-#if defined(HAVE_LIBDRM) && defined(HAVE_LINUX_UDMABUF_H)
+#if defined(HAVE_LIBDRM) && DETECT_OS_POSIX
       struct llvmpipe_memory_allocation *alloc;
       uint64_t size;
       /* Not all winsys implement displaytarget_create_mapped so we need to check
@@ -787,8 +788,10 @@
          lpr->dt = winsys->displaytarget_create_mapped(winsys, template->bind,
                                                        template->format, template->width0, template->height0,
                                                        whandle->stride, data, whandle);
-         if (!lpr->dt)
+         if (!lpr->dt) {
+            _screen->free_memory_fd(_screen, (struct pipe_memory_allocation *)alloc);
             goto no_dt;
+         }
          lpr->dmabuf_alloc = alloc;
          lpr->dmabuf = true;
          lpr->tex_data = data;
@@ -1398,7 +1401,7 @@
 }
 
 
-#if defined(HAVE_LIBDRM) && defined(HAVE_LINUX_UDMABUF_H)
+#if defined(HAVE_LIBDRM) && DETECT_OS_POSIX
 static void
 llvmpipe_dmabuf_free(struct llvmpipe_memory_allocation *alloc)
 {
@@ -1434,6 +1437,9 @@
    return true;
 }
 
+#endif
+
+#if defined(HAVE_LIBDRM) && defined(HAVE_LINUX_UDMABUF_H)
 static bool
 llvmpipe_dmabuf_alloc(struct llvmpipe_screen *screen,
                        size_t size,
@@ -1566,7 +1572,7 @@
    if (dup_fd < 0)
       goto fail;
 
-#if defined(HAVE_LIBDRM) && defined(HAVE_LINUX_UDMABUF_H)
+#if defined(HAVE_LIBDRM) && DETECT_OS_POSIX
    if (dmabuf) {
       if (!llvmpipe_dmabuf_import(dup_fd, alloc))
          goto fail;
@@ -1601,7 +1607,7 @@
       os_free_fd(alloc->cpu_addr);
       close(alloc->fd);
    }
-#if defined(HAVE_LIBDRM) && defined(HAVE_LINUX_UDMABUF_H)
+#if defined(HAVE_LIBDRM) && DETECT_OS_POSIX
    else {
       llvmpipe_dmabuf_free(alloc);
    }
