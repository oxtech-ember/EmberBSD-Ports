$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Include the standard header declaring std::alignment_of.
--- common/sys/vector.h
+++ common/sys/vector.h
@@ -5,6 +5,7 @@
 
 #include "alloc.h"
 #include <algorithm>
+#include <type_traits>
 
 namespace embree
 {
