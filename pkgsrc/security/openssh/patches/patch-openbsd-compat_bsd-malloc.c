$NetBSD$

Declare the selected allocator replacements before defining them.

--- openbsd-compat/bsd-malloc.c.orig
+++ openbsd-compat/bsd-malloc.c
@@ -21,6 +21,16 @@
 
 #include <sys/types.h>
 #include <stdlib.h>
+
+#if defined(HAVE_MALLOC) && HAVE_MALLOC == 0
+void *rpl_malloc(size_t);
+#endif
+#if defined(HAVE_CALLOC) && HAVE_CALLOC == 0
+void *rpl_calloc(size_t, size_t);
+#endif
+#if defined(HAVE_REALLOC) && HAVE_REALLOC == 0
+void *rpl_realloc(void *, size_t);
+#endif
 
 #if defined(HAVE_MALLOC) && HAVE_MALLOC == 0
 void *
