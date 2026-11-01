$NetBSD$

Include <iterator> for std::inserter. The target C++ headers no longer provide it
through the other standard headers included here.

--- gtsam/nonlinear/ISAM2-impl.h.orig
+++ gtsam/nonlinear/ISAM2-impl.h
@@ -34,6 +34,7 @@
 #include <utility>
 #include <variant>
 #include <cassert>
+#include <iterator>
 
 namespace gtsam {
 
