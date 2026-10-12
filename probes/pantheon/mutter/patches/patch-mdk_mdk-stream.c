$NetBSD$

--- mdk/mdk-stream.c.orig	2026-09-15 17:26:39.000000000 +0300
+++ mdk/mdk-stream.c	2026-10-12 23:45:15.284757891 +0300
@@ -26,7 +26,9 @@
 #include <gio/gio.h>
 #include <gdk/gdk.h>
 #include <gtk/gtk.h>
+#ifdef __linux__
 #include <linux/dma-buf.h>
+#endif
 #include <pipewire/keys.h>
 #include <pipewire/stream.h>
 #include <spa/debug/format.h>
