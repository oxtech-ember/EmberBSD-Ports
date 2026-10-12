$NetBSD$

--- src/backends/native/meta-kms-impl-device.c.orig	2025-03-04 22:59:55.000000000 +0300
+++ src/backends/native/meta-kms-impl-device.c	2026-10-12 21:37:30.572587528 +0300
@@ -21,7 +21,9 @@
 
 #include <errno.h>
 #include <glib/gstdio.h>
+#ifdef __linux__
 #include <linux/dma-buf.h>
+#endif
 #include <sys/ioctl.h>
 #include <sys/timerfd.h>
 #include <xf86drm.h>
