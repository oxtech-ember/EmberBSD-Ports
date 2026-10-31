$NetBSD$

Bring the release library to upstream a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988.
https://github.com/cr-marcstevens/sha1collisiondetection/compare/stable-v1.0.3...a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988

--- lib/ubc_check.h.orig
+++ lib/ubc_check.h
@@ -27,7 +27,9 @@
 extern "C" {
 #endif
 
+#ifndef SHA1DC_NO_STANDARD_INCLUDES
 #include <stdint.h>
+#endif
 
 #define DVMASKSIZE 1
 typedef struct { int dvType; int dvK; int dvB; int testt; int maski; int maskb; uint32_t dm[80]; } dv_info_t;
@@ -43,4 +45,8 @@
 }
 #endif
 
+#ifdef SHA1DC_CUSTOM_TRAILING_INCLUDE_UBC_CHECK_H
+#include SHA1DC_CUSTOM_TRAILING_INCLUDE_UBC_CHECK_H
 #endif
+
+#endif
