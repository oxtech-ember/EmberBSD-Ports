$NetBSD$

Resolve the Darwin loader prefix from the GdkPixbuf library.

--- gdk-pixbuf/queryloaders.c.orig
+++ gdk-pixbuf/queryloaders.c
@@ -132,14 +132,7 @@
 #if defined (G_OS_WIN32)
                 toplevel = g_win32_get_package_installation_directory_of_module (NULL);
 #elif defined(OS_DARWIN)
-                char pathbuf[PATH_MAX + 1];
-                uint32_t bufsize = sizeof (pathbuf);
-                gchar *bin_dir;
-
-                _NSGetExecutablePath (pathbuf, &bufsize);
-                bin_dir = g_dirname (pathbuf);
-                toplevel = g_build_path (G_DIR_SEPARATOR_S, bin_dir, "..", NULL);
-                g_free (bin_dir);
+                toplevel = gdk_pixbuf_darwin_prefix ();
 #elif defined (OS_LINUX) || defined (__MINGW32__)
                 gchar *exe_path, *bin_dir;
 
@@ -280,7 +273,7 @@
         g_free (path);
 }
 
-#if defined(G_OS_WIN32) && defined(GDK_PIXBUF_RELOCATABLE)
+#if (defined(G_OS_WIN32) || defined(OS_DARWIN)) && defined(GDK_PIXBUF_RELOCATABLE)
 
 static char *
 get_libdir (void)
@@ -316,7 +309,9 @@
         GString *contents;
         gchar *cache_file = NULL;
         gint first_file = 1;
+#if !defined(OS_DARWIN) || !defined(GDK_PIXBUF_RELOCATABLE)
         GFile *pixbuf_libdir_file;
+#endif
         gchar *pixbuf_libdir;
 
 #ifdef G_OS_WIN32
@@ -325,12 +320,17 @@
         gchar *pixbuf_prefix;
 #endif
 
+#if defined(OS_DARWIN) && defined(GDK_PIXBUF_RELOCATABLE)
+        pixbuf_libdir = g_build_filename (get_libdir (), "gdk-pixbuf-2.0",
+                                          GDK_PIXBUF_BINARY_VERSION, "loaders", NULL);
+#else
         /* An intermediate GFile here will convert all the path separators
          * to the right one used by the platform
          */
         pixbuf_libdir_file = g_file_new_for_path (PIXBUF_LIBDIR);
         pixbuf_libdir = g_file_get_path (pixbuf_libdir_file);
         g_object_unref (pixbuf_libdir_file);
+#endif
 
 #ifdef G_OS_WIN32
         pixbuf_prefix_file = g_file_new_for_path (GDK_PIXBUF_PREFIX);
