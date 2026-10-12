$NetBSD$

--- cogl/cogl/cogl-dma-buf-handle.c.orig	2026-09-15 17:26:39.000000000 +0300
+++ cogl/cogl/cogl-dma-buf-handle.c	2026-10-12 23:45:15.283296718 +0300
@@ -36,7 +36,30 @@
 #include <errno.h>
 #include <gio/gio.h>
 #include <glib/gstdio.h>
+#ifdef __linux__
 #include <linux/dma-buf.h>
+#else
+#include <stdint.h>
+#include <sys/ioccom.h>
+
+/* Local definitions of the Linux dma-buf UAPI on systems without
+ * <linux/dma-buf.h>. Mirrors upstream uapi/linux/dma-buf.h. */
+typedef uint64_t __u64;
+
+struct dma_buf_sync
+{
+  __u64 flags;
+};
+
+#define DMA_BUF_SYNC_READ  (1 << 0)
+#define DMA_BUF_SYNC_WRITE (2 << 0)
+#define DMA_BUF_SYNC_RW    (DMA_BUF_SYNC_READ | DMA_BUF_SYNC_WRITE)
+#define DMA_BUF_SYNC_START (0 << 2)
+#define DMA_BUF_SYNC_END   (1 << 2)
+#define DMA_BUF_SYNC_VALID_FLAGS_MASK (DMA_BUF_SYNC_RW | DMA_BUF_SYNC_END)
+#define DMA_BUF_BASE       'b'
+#define DMA_BUF_IOCTL_SYNC _IOW(DMA_BUF_BASE, 0, struct dma_buf_sync)
+#endif
 #include <sys/ioctl.h>
 #include <sys/mman.h>
 #include <unistd.h>
