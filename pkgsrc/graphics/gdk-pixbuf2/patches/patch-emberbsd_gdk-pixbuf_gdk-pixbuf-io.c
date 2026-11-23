$NetBSD$

Resolve the Darwin loader prefix from the GdkPixbuf library.

--- gdk-pixbuf/gdk-pixbuf-io.c.orig
+++ gdk-pixbuf/gdk-pixbuf-io.c
@@ -216,14 +216,7 @@
 #if defined(G_OS_WIN32)
     toplevel = g_win32_get_package_installation_directory_of_module (gdk_pixbuf_dll);
 #elif defined(OS_DARWIN)
-    char pathbuf[PATH_MAX + 1];
-    uint32_t  bufsize = sizeof(pathbuf);
-    gchar *bin_dir;
-
-    _NSGetExecutablePath(pathbuf, &bufsize);
-    bin_dir = g_dirname(pathbuf);
-    toplevel = g_build_path (G_DIR_SEPARATOR_S, bin_dir, "..", NULL);
-    g_free (bin_dir);
+    toplevel = gdk_pixbuf_darwin_prefix ();
 #elif defined (OS_LINUX)
     gchar *exe_path, *bin_dir;
 
