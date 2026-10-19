$NetBSD$

Use NetBSD byte-order definitions for BlueZ codec bitfields.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- src/a2dp-codecs.h.orig
+++ src/a2dp-codecs.h
@@ -10,7 +10,22 @@
 #ifndef BLUEZQT_A2DPCODECS_H
 #define BLUEZQT_A2DPCODECS_H
 
+#if defined(__NetBSD__)
+#include <sys/endian.h>
+#define BLUEZQT_BYTE_ORDER _BYTE_ORDER
+#define BLUEZQT_LITTLE_ENDIAN _LITTLE_ENDIAN
+#define BLUEZQT_BIG_ENDIAN _BIG_ENDIAN
+#elif defined(__APPLE__)
+#include <machine/endian.h>
+#define BLUEZQT_BYTE_ORDER BYTE_ORDER
+#define BLUEZQT_LITTLE_ENDIAN LITTLE_ENDIAN
+#define BLUEZQT_BIG_ENDIAN BIG_ENDIAN
+#else
 #include <endian.h>
+#define BLUEZQT_BYTE_ORDER __BYTE_ORDER
+#define BLUEZQT_LITTLE_ENDIAN __LITTLE_ENDIAN
+#define BLUEZQT_BIG_ENDIAN __BIG_ENDIAN
+#endif
 #include <stdint.h>
 
 // clang-format off
@@ -142,7 +157,7 @@
 	uint16_t codec_id;
 } __attribute__ ((packed)) a2dp_vendor_codec_t;
 
-#if __BYTE_ORDER == __LITTLE_ENDIAN
+#if BLUEZQT_BYTE_ORDER == BLUEZQT_LITTLE_ENDIAN
 
 typedef struct {
 	uint8_t channel_mode:4;
@@ -187,7 +202,7 @@
 	uint8_t unknown[2];
 } __attribute__ ((packed)) a2dp_ldac_t;
 
-#elif __BYTE_ORDER == __BIG_ENDIAN
+#elif BLUEZQT_BYTE_ORDER == BLUEZQT_BIG_ENDIAN
 
 typedef struct {
 	uint8_t frequency:4;
