$NetBSD$

Map the NetBSD endian macros onto the names used here.

--- src/a2dp-codecs.h.orig
+++ src/a2dp-codecs.h
@@ -12,6 +12,11 @@
 
 #include <endian.h>
 #include <stdint.h>
+#if !defined(__BYTE_ORDER) && defined(_BYTE_ORDER)
+#define __BYTE_ORDER _BYTE_ORDER
+#define __LITTLE_ENDIAN _LITTLE_ENDIAN
+#define __BIG_ENDIAN _BIG_ENDIAN
+#endif
 
 // clang-format off
 
