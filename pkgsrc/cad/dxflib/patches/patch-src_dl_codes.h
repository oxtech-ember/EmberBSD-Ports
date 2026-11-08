$NetBSD$

Guard the Windows compatibility macro when the platform already defines it.
--- src/dl_codes.h.orig
+++ src/dl_codes.h
@@ -40,7 +40,7 @@
 #define strcasecmp(s,t) stricmp(s,t)
 #endif
 
-#if defined(_WIN32)
+#if defined(_WIN32) && !defined(strcasecmp)
 #define strcasecmp(s,t) _stricmp(s,t)
 #endif
 
