$NetBSD$

Include <cstdlib> for exit() and atoi(). The target C++ headers no longer provide
them through <string> or <thread>.

--- examples/bench/bench.cpp.orig
+++ examples/bench/bench.cpp
@@ -1,6 +1,7 @@
 #include "whisper.h"
 
 #include <cstdio>
+#include <cstdlib>
 #include <cstring>
 #include <string>
 #include <thread>
