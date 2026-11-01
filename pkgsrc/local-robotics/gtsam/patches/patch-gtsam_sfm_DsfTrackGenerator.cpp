$NetBSD$

Include <iterator> for std::back_inserter. The target C++ headers no longer
provide it through the other standard headers included here.

--- gtsam/sfm/DsfTrackGenerator.cpp.orig
+++ gtsam/sfm/DsfTrackGenerator.cpp
@@ -20,6 +20,7 @@
 
 #include <algorithm>
 #include <iostream>
+#include <iterator>
 #include <iomanip>
 
 namespace gtsam {
