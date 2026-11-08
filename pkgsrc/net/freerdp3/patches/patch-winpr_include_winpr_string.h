$NetBSD$

NetBSD does not expose va_list from the headers included here.

--- winpr/include/winpr/string.h.orig
+++ winpr/include/winpr/string.h
@@ -24,6 +24,7 @@
 #include <wchar.h>
 #include <stdio.h>
 #include <string.h>
+#include <stdarg.h>
 #include <winpr/config.h>
 #include <winpr/winpr.h>
 #include <winpr/wtypes.h>
