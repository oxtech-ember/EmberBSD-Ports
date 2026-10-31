$NetBSD$

Fall back to CLOCK_MONOTONIC where CLOCK_MONOTONIC_RAW is missing (NetBSD).

--- spa/plugins/support/logger.c.orig
+++ spa/plugins/support/logger.c
@@ -22,7 +22,11 @@
 
 #if defined(__FreeBSD__) || defined(__MidnightBSD__)
 #define CLOCK_MONOTONIC_RAW CLOCK_MONOTONIC
-#elif defined(_MSC_VER)
+#elif !defined(_MSC_VER) && !defined(CLOCK_MONOTONIC_RAW)
+/* No raw (unslewed) monotonic clock, e.g. NetBSD: use the monotonic one. */
+#define CLOCK_MONOTONIC_RAW CLOCK_MONOTONIC
+#endif
+#if defined(_MSC_VER)
 static inline void setlinebuf(FILE* stream) {
 	setvbuf(stream, NULL, _IOLBF, 0);
 }
