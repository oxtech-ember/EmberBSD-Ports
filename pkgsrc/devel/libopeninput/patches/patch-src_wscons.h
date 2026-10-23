$NetBSD: patch-src_wscons.h,v 1.1 2026/04/13 15:19:37 kikadf Exp $

* Handle attached-detached devices with udev monitor

Refreshed for libopeninput 1.31.3 context (usec_t); behavior retained.

--- src/wscons.h.orig
+++ src/wscons.h
@@ -25,6 +25,12 @@
 	} pointer;
 };
 
+struct udev_input {
+	struct libinput base;
+	struct udev *udev;
+	struct udev_monitor *udev_monitor;
+	struct libinput_source *udev_monitor_source;
+};
 
 static inline struct wscons_device *
 wscons_device(struct libinput_device *device)
