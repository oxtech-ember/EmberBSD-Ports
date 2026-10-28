$NetBSD$

Allow freestanding consumers to supply their platform header glue.
Origin: EmberBSD (AI-assisted); upstream status: not submitted.

--- C/7zTypes.h.orig
+++ C/7zTypes.h
@@ -7,7 +7,9 @@
 #ifdef _WIN32
 /* #include <windows.h> */
 #else
+#ifndef Z7_FREESTANDING
 #include <errno.h>
+#endif
 #endif
 
 #include <stddef.h>
