$NetBSD$

bundle.cpp uses std::vector; include <vector> instead of relying on a
transitive include, which current libc++ no longer provides.

--- bundle.cpp.orig
+++ bundle.cpp
@@ -5,6 +5,7 @@
 #include <stdexcept>
 #include <sys/stat.h>
 #include <unistd.h>
+#include <vector>
 
 #include <plist/plist.h>
 
