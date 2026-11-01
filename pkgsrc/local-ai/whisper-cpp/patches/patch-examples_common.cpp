$NetBSD$

Include <algorithm> for std::partial_sort. The target C++ headers no
longer provide it through the other standard headers used here.

--- examples/common.cpp.orig
+++ examples/common.cpp
@@ -2,6 +2,7 @@
 
 #include "common.h"
 
+#include <algorithm>
 #include <cmath>
 #include <codecvt>
 #include <cstring>
