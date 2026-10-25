$NetBSD$

Keep one explicit STL ABI across the library and its consumers.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- simplecpp.h.orig
+++ simplecpp.h
@@ -5,6 +5,8 @@
 
 #ifndef simplecppH
 #define simplecppH
+
+#include "simplecpp-abi.h"
 
 #include <cctype>
 #include <cstdint>
