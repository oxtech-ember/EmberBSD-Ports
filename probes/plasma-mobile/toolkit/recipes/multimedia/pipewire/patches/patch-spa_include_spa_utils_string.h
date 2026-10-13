$NetBSD$

NetBSD has newlocale but no uselocale; use the plain C-locale
conversion path that upstream provides for such systems.

--- spa/include/spa/utils/string.h.orig	2026-10-13
+++ spa/include/spa/utils/string.h
@@ -5,6 +5,11 @@
 #ifndef SPA_UTILS_STRING_H
 #define SPA_UTILS_STRING_H
 
+/* NetBSD has newlocale but no uselocale; use the plain C-locale path. */
+#if defined(__NetBSD__) && !defined(__LOCALE_C_ONLY)
+#define __LOCALE_C_ONLY
+#endif
+
 #include <stdarg.h>
 #include <stdbool.h>
 #include <errno.h>
