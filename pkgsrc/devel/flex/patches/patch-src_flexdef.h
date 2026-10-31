$NetBSD$

Build stage1flex without NLS when cross compiling. It is built with the
build machine compiler, but config.h describes the target, whose NLS
needs <libintl.h>. Upstream uses config_for_build.h for this
(https://github.com/westes/flex/commit/0774131f06f8350da14ef6521adbfcd7b8481ce7).

--- src/flexdef.h.orig
+++ src/flexdef.h
@@ -39,6 +39,15 @@
 #include <config.h>
 #endif
 
+/* stage1flex is built with the build machine compiler, but config.h
+   describes the host flex is configured for.  stage1flex only generates
+   the scanner, so build it without NLS, as config_for_build.h does
+   upstream.  */
+#ifdef USE_CONFIG_FOR_BUILD
+#undef ENABLE_NLS
+#undef HAVE_LOCALE_H
+#endif
+
 #include <stdio.h>
 #include <stdlib.h>
 #include <stdarg.h>
