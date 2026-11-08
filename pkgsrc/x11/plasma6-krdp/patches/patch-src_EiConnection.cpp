$NetBSD$

Use the libei evdev button numbers without linux/input.h.

--- src/EiConnection.cpp.orig
+++ src/EiConnection.cpp
@@ -10,7 +10,16 @@
 #include <QWheelEvent>
 
 #include <libei.h>
+#if defined(__linux__)
 #include <linux/input.h>
+#else
+// libei uses the Linux evdev button numbers. NetBSD has no linux/input.h.
+constexpr int BTN_LEFT = 0x110;
+constexpr int BTN_RIGHT = 0x111;
+constexpr int BTN_MIDDLE = 0x112;
+constexpr int BTN_SIDE = 0x113;
+constexpr int BTN_EXTRA = 0x114;
+#endif
 
 #include "krdp_logging.h"
 
