$NetBSD$

Refresh the existing pkgsrc platform adaptation for WebKitGTK 2.54.1.
Origin: EmberBSD (AI-assisted), based on the pinned pkgsrc patch; not submitted upstream.

--- Source/WebCore/platform/graphics/gbm/MemoryMappedGPUBuffer.cpp.orig
+++ Source/WebCore/platform/graphics/gbm/MemoryMappedGPUBuffer.cpp
@@ -36,7 +36,9 @@
 #include "VivanteSuperTiledTextureInlines.h"
 #include <epoxy/egl.h>
 #include <fcntl.h>
+#ifdef __linux__
 #include <linux/dma-buf.h>
+#endif
 #include <sys/ioctl.h>
 #include <sys/mman.h>
 #include <unistd.h>
@@ -508,6 +510,7 @@
 
 bool MemoryMappedGPUBuffer::performDMABufSyncSystemCall(OptionSet<DMABufSyncFlag> flags)
 {
+#ifdef __linux__
     constexpr unsigned maxRetries = 10;
 
     struct dma_buf_sync sync;
@@ -537,6 +540,9 @@
     }
 
     return true;
+#else
+    return false;
+#endif
 }
 
 } // namespace WebCore
