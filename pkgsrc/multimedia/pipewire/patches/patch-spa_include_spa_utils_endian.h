$NetBSD$

NetBSD provides bswap16/32/64 through <sys/endian.h> like FreeBSD
and has no <byteswap.h>; the macOS host tools use OSSwapInt.

--- spa/include/spa/utils/endian.h.orig	2026-10-13
+++ spa/include/spa/utils/endian.h
@@ -5,11 +5,16 @@
 #ifndef SPA_ENDIAN_H
 #define SPA_ENDIAN_H
 
-#if defined(__FreeBSD__) || defined(__MidnightBSD__)
+#if defined(__FreeBSD__) || defined(__MidnightBSD__) || defined(__NetBSD__)
 #include <sys/endian.h>
 #define bswap_16 bswap16
 #define bswap_32 bswap32
 #define bswap_64 bswap64
+#elif defined(__APPLE__)
+#include <libkern/OSByteOrder.h>
+#define bswap_16 OSSwapInt16
+#define bswap_32 OSSwapInt32
+#define bswap_64 OSSwapInt64
 #elif defined(_MSC_VER) && defined(_WIN32)
 #include <stdlib.h>
 #define __LITTLE_ENDIAN 1234
