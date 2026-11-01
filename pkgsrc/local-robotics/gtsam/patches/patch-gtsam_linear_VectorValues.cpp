$NetBSD$

Include <iterator> for std::inserter. The target C++ headers no longer provide it
through <functional> or <map>.

--- gtsam/linear/VectorValues.cpp.orig
+++ gtsam/linear/VectorValues.cpp
@@ -19,6 +19,7 @@
 #include <gtsam/linear/VectorValues.h>
 
 #include <functional>
+#include <iterator>
 #include <utility>
 
 // assert_throw needs a semicolon in Release mode.
