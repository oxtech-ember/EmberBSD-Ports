$NetBSD$

Use the same CMake libspnav selection as the editor modules.

--- common/spacenav/libspnav_driver.h.orig
+++ common/spacenav/libspnav_driver.h
@@ -24,7 +24,9 @@
 #ifndef KICAD_LIBSPNAV_DRIVER_H
 #define KICAD_LIBSPNAV_DRIVER_H
 
-#if defined(__linux__) || defined(__FreeBSD__)
+#include <config.h>
+
+#if SPNAV_FOUND
 #include <spnav.h>
 #endif
 
