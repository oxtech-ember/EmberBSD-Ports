$NetBSD$

--- src/backends/native/meta-kms-impl-device.c.orig	2026-09-15 17:26:39.000000000 +0300
+++ src/backends/native/meta-kms-impl-device.c	2026-10-12 23:45:15.284343347 +0300
@@ -22,7 +22,9 @@
 #include <errno.h>
 #include <fcntl.h>
 #include <glib/gstdio.h>
+#ifdef __linux__
 #include <linux/dma-buf.h>
+#endif
 #include <poll.h>
 #include <sys/ioctl.h>
 #include <sys/timerfd.h>
