$NetBSD$

Include the shared libspnav interface on NetBSD as selected by CMake.

--- common/spacenav/libspnav_driver.h.orig
+++ common/spacenav/libspnav_driver.h
@@ -24,7 +24,7 @@
 #ifndef KICAD_LIBSPNAV_DRIVER_H
 #define KICAD_LIBSPNAV_DRIVER_H
 
-#if defined(__linux__) || defined(__FreeBSD__)
+#if defined(__linux__) || defined(__FreeBSD__) || defined(__NetBSD__)
 #include <spnav.h>
 #endif
 
