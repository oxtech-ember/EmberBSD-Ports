$NetBSD$

Locate the built-in macOS resource paths relative to the executable.
Keep explicit search directories unchanged.
Origin: EmberBSD (AI-assisted).

--- src/libs/libgroff/searchpath.cpp.orig
+++ src/libs/libgroff/searchpath.cpp
@@ -34,6 +34,11 @@
 
 #include "searchpath.h"
 #include "nonposix.h"
+
+#if defined __APPLE__
+# include <string>
+# include "relocate.h"
+#endif
 
 #ifdef _WIN32
 # include "relocate.h"
@@ -55,6 +60,26 @@
 search_path::search_path(const char *envvar, const char *standard,
 			 int add_home, int add_current)
 {
+#ifdef __APPLE__
+  // Relocate compiled defaults. Keep user-supplied -F, -M and
+  // environment paths unchanged.
+  std::string defaults;
+  if (standard && *standard) {
+    const char *start = standard;
+    for (;;) {
+      const char *end = strchr(start, PATH_SEP_CHAR);
+      std::string component(start, end ? end - start : strlen(start));
+      char *path = relocatep(component.c_str());
+      defaults += path;
+      free(path);
+      if (!end)
+        break;
+      defaults += PATH_SEP_CHAR;
+      start = end + 1;
+    }
+    standard = defaults.c_str();
+  }
+#endif
   char *home = 0 /* nullptr */;
   if (add_home)
     home = getenv("HOME");
