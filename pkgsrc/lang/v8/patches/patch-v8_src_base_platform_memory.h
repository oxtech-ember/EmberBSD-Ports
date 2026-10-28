$NetBSD$

Combine BSD allocation headers and safe usable-size selection.
Origin: NetBSD pkgsrc Node and Chromium patches; FreeBSD uses malloc_np.h.

--- src/base/platform/memory.h.orig
+++ src/base/platform/memory.h
@@ -21,13 +21,15 @@
 #include <malloc/malloc.h>
 #elif V8_OS_OPENBSD
 #include <sys/malloc.h>
-#elif V8_OS_ZOS
+#elif V8_OS_FREEBSD
+#include <malloc_np.h>
+#elif V8_OS_ZOS || V8_OS_NETBSD
 #include <stdlib.h>
 #else
 #include <malloc.h>
 #endif
 
-#if (V8_OS_POSIX && !V8_OS_AIX && !V8_OS_SOLARIS && !V8_OS_ZOS && !V8_OS_OPENBSD) || V8_OS_WIN
+#if (V8_OS_POSIX && !V8_OS_AIX && !V8_OS_SOLARIS && !V8_OS_ZOS && !V8_OS_OPENBSD && !V8_OS_NETBSD) || V8_OS_WIN
 #define V8_HAS_MALLOC_USABLE_SIZE 1
 #endif
 
