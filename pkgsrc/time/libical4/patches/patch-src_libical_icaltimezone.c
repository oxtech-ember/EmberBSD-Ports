$NetBSD$

Locate optional builtin timezone data relative to the installed Darwin library.

--- src/libical/icaltimezone.c.orig
+++ src/libical/icaltimezone.c
@@ -52,6 +52,11 @@
 #include <mbstring.h>
 #endif
 #include <windows.h>
+#endif
+
+#if defined(__APPLE__)
+#include <dlfcn.h>
+#include <pthread.h>
 #endif
 
 /** This is the toplevel directory where the timezone data is installed in. */
@@ -2187,9 +2192,42 @@
 #pragma GCC diagnostic pop
 #endif
 
+#if defined(__APPLE__)
+static pthread_once_t builtin_zone_once = PTHREAD_ONCE_INIT;
+static char builtin_zone_dir[MAXPATHLEN];
+
+/* The optional iCalendar zone files live under the prefix of this library. */
+static void locate_builtin_zone_dir(void)
+{
+    Dl_info image;
+    char path[MAXPATHLEN];
+
+    if (dladdr((const void *)&icaltimezone_get_zone_directory, &image) == 0 ||
+        image.dli_fname == NULL || realpath(image.dli_fname, path) == NULL) {
+        return;
+    }
+    char *slash = strrchr(path, '/');
+    if (slash == NULL) {
+        return;
+    }
+    *slash = '\0';
+    int length = snprintf(builtin_zone_dir, sizeof(builtin_zone_dir),
+                          "%s/../share/libical/zoneinfo", path);
+    if (length < 0 || (size_t)length >= sizeof(builtin_zone_dir)) {
+        builtin_zone_dir[0] = '\0';
+    }
+}
+#endif
+
 static const char *get_zone_directory_builtin(void)
 {
-#if !defined(_WIN32)
+#if defined(__APPLE__)
+    if (zone_files_directory != NULL) {
+        return zone_files_directory;
+    }
+    pthread_once(&builtin_zone_once, locate_builtin_zone_dir);
+    return builtin_zone_dir[0] == '\0' ? NULL : builtin_zone_dir;
+#elif !defined(_WIN32)
     return zone_files_directory == NULL ? ZONEINFO_DIRECTORY : zone_files_directory;
 #else
     wchar_t wbuffer[1000];
