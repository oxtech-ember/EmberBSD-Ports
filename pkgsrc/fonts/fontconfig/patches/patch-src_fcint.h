$NetBSD: patch-src_fcint.h,v 1.4 2025/08/10 13:58:35 ryoon Exp $

Relocate prefix-owned runtime defaults using the loaded shared library.
Preserve upstream platform fixes and explicit caller configuration.
Additional changes: EmberBSD contributors (AI-assisted).

--- src/fcint.h.orig
+++ src/fcint.h
@@ -97,6 +97,17 @@
 #  define FC_PATH_MAX 128
 #endif
 
+/*
+ * SCO OpenServer 5.0.7/3.2 has no MAXPATHLEN, but it has PATH_MAX (256).
+ * in limits.h. PATH_MAX is defined alternatively under non-OpenServer OS,
+ * and it is used in dirname.c of bmake.
+ */
+#if !defined(PATH_MAX)
+#if defined(_SCO_DS)
+#define PATH_MAX	1024
+#endif
+#endif
+
 #if __GNUC__ >= 4
 #  define FC_UNUSED __attribute__ ((unused))
 #else
@@ -128,7 +139,13 @@
 #define FC_MAX(a, b)                     ((a) > (b) ? (a) : (b))
 
 /* slim_internal.h */
-#if (__GNUC__ > 3 || (__GNUC__ == 3 && __GNUC_MINOR__ >= 3)) && defined(__ELF__) && !defined(__sun) && !defined(BINDGEN_IGNORE_VISIBILITY)
+/* Bug of GCC 4.2 (visibility and -fPIC)
+   http://gcc.gnu.org/bugzilla/show_bug.cgi?id=46861 */
+#if (__GNUC__ == 4 && __GNUC_MINOR__ == 2) && defined(__ELF__) && !defined(__sun)
+#define FcPrivate
+#define HAVE_GNUC_ATTRIBUTE 1
+#include "fcalias.h"
+#elif (__GNUC__ > 3 || (__GNUC__ == 3 && __GNUC_MINOR__ >= 3)) && defined(__ELF__) && !defined(__sun) && !defined(BINDGEN_IGNORE_VISIBILITY)
 #  define FcPrivate           __attribute__ ((__visibility__ ("hidden")))
 #  define HAVE_GNUC_ATTRIBUTE 1
 #  include "fcalias.h"
@@ -761,6 +778,9 @@
 FcDirCacheUnlock (int fd);
 
 /* fccfg.c */
+
+FcPrivate FcChar8 *
+FcConfigRelocatePath (const FcChar8 *path);
 
 FcPrivate FcBool
 FcConfigInit (void);
