$NetBSD$

Origin: EmberBSD (AI-assisted). Not submitted upstream.
Use the current locale codeset explicitly; iconv's empty-name extension is
not provided by EmberBSD libc. Preserve strict conversion failure behavior.

--- src/pulse/utf8.c.orig
+++ src/pulse/utf8.c
@@ -51,6 +51,9 @@
 
 #ifdef HAVE_ICONV
 #include <iconv.h>
+#ifdef HAVE_LANGINFO_H
+#include <langinfo.h>
+#endif
 #endif
 
 #include <pulse/xmalloc.h>
@@ -198,6 +201,13 @@
     pa_assert(to);
     pa_assert(from);
 
+#if defined(HAVE_LANGINFO_H) && defined(CODESET)
+    if (!*to)
+        to = nl_langinfo(CODESET);
+    if (!*from)
+        from = nl_langinfo(CODESET);
+#endif
+
     cd = iconv_open(to, from);
     if (cd == (iconv_t)-1)
         return NULL;
