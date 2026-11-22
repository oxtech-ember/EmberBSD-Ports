$NetBSD$

Locate the built-in macOS resource paths relative to the executable.
Keep explicit search directories unchanged.
Origin: EmberBSD (AI-assisted).

--- src/libs/libgroff/relocate.cpp.orig
+++ src/libs/libgroff/relocate.cpp
@@ -37,6 +37,8 @@
 #if defined _WIN32
 # define WIN32_LEAN_AND_MEAN
 # include <windows.h>
+#elif defined __APPLE__
+# include <mach-o/dyld.h>
 #endif
 
 #define INSTALLPATHLEN (sizeof(INSTALLPATH) - 1)
@@ -192,6 +194,15 @@
     delete[] pathextstr;
   }
   msw2posixpath(curr_prefix);
+#elif defined __APPLE__
+  uint32_t size = 0;
+  _NSGetExecutablePath(0, &size);
+  char *image = new char[size];
+  if (_NSGetExecutablePath(image, &size) == 0)
+    curr_prefix = realpath(image, 0);
+  delete[] image;
+  if (!curr_prefix)
+    return;
 #else /* !_WIN32 */
   curr_prefix = searchpath(program_name, getenv("PATH"));
   if (!curr_prefix)
@@ -218,10 +229,20 @@
   fprintf(stderr, "relocatep: INSTALLPATH = %s\n", INSTALLPATH);
   fprintf(stderr, "relocatep: INSTALLPATHLEN = %d\n", INSTALLPATHLEN);
 #endif
+#ifdef __APPLE__
+  if (strncmp(INSTALLPATH, path, INSTALLPATHLEN)
+      || !strchr(DIR_SEPS, path[INSTALLPATHLEN]))
+    return strsave(path);
+#endif
   if (!curr_prefix)
     set_current_prefix();
+#ifdef __APPLE__
+  if (!curr_prefix)
+    return strsave(path);
+#else
   if (strncmp(INSTALLPATH, path, INSTALLPATHLEN))
     return strsave(path);
+#endif
   char *relative_path = (char *)path + INSTALLPATHLEN;
   size_t relative_path_len = strlen(relative_path);
   char *relocated_path = (char *)malloc(curr_prefix_len
