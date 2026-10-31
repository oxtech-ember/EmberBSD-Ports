$NetBSD$

NetBSD has no ECHRNG errno, which the spa audio headers return for a
channel count or position out of range. Use ERANGE where it is missing.

--- spa/include/spa/utils/defs.h.orig
+++ spa/include/spa/utils/defs.h
@@ -11,6 +11,13 @@
 #include <string.h>
 #include <stddef.h>
 #include <stdio.h>
+#include <errno.h>
+
+/* NetBSD and macOS have no ECHRNG; the headers report a channel count
+ * or position out of range, so use ERANGE. */
+#ifndef ECHRNG
+#define ECHRNG ERANGE
+#endif
 
 #ifdef __cplusplus
 extern "C" {
