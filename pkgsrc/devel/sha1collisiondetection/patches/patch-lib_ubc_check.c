$NetBSD$

Bring the release library to upstream a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988.
https://github.com/cr-marcstevens/sha1collisiondetection/compare/stable-v1.0.3...a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988

--- lib/ubc_check.c.orig
+++ lib/ubc_check.c
@@ -24,7 +24,12 @@
 // ubc_check has been verified against ubc_check_verify using the 'ubc_check_test' program in the tools section
 */
 
+#ifndef SHA1DC_NO_STANDARD_INCLUDES
 #include <stdint.h>
+#endif
+#ifdef SHA1DC_CUSTOM_INCLUDE_UBC_CHECK_C
+#include SHA1DC_CUSTOM_INCLUDE_UBC_CHECK_C
+#endif
 #include "ubc_check.h"
 
 static const uint32_t DV_I_43_0_bit 	= (uint32_t)(1) << 0;
@@ -361,3 +366,7 @@
 
 	dvmask[0]=mask;
 }
+
+#ifdef SHA1DC_CUSTOM_TRAILING_INCLUDE_UBC_CHECK_C
+#include SHA1DC_CUSTOM_TRAILING_INCLUDE_UBC_CHECK_C
+#endif
