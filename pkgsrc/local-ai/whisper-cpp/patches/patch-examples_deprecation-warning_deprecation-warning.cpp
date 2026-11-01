$NetBSD$

Include <cstdlib> for EXIT_FAILURE. The target C++ headers no longer
provide it through <string>.

--- examples/deprecation-warning/deprecation-warning.cpp.orig
+++ examples/deprecation-warning/deprecation-warning.cpp
@@ -1,6 +1,7 @@
 // Warns users that this filename was deprecated, and provides a link for more information.
 
 #include <cstdio>
+#include <cstdlib>
 #include <string>
 
 // Main
