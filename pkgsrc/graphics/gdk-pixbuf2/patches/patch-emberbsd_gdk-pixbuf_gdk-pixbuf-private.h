$NetBSD$

Resolve the Darwin loader prefix from the GdkPixbuf library.

--- gdk-pixbuf/gdk-pixbuf-private.h.orig
+++ gdk-pixbuf/gdk-pixbuf-private.h
@@ -130,6 +130,25 @@
 
 void _gdk_pixbuf_init_gettext (void);
 
+#if defined(OS_DARWIN) && defined(GDK_PIXBUF_RELOCATABLE)
+#include <dlfcn.h>
+
+/* Locate the library that owns the loaders and the cache. */
+static inline gchar *
+gdk_pixbuf_darwin_prefix (void)
+{
+        Dl_info image;
+        gchar *libdir;
+        gchar *prefix;
+
+        g_return_val_if_fail (dladdr ((const void *) gdk_pixbuf_get_type, &image) != 0, NULL);
+        libdir = g_path_get_dirname (image.dli_fname);
+        prefix = g_path_get_dirname (libdir);
+        g_free (libdir);
+        return prefix;
+}
+#endif
+
 #endif /* GDK_PIXBUF_PRIVATE_H */
 
 #ifdef GDK_PIXBUF_RELOCATABLE
