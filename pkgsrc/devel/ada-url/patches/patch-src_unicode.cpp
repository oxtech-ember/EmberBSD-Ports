# $NetBSD$

Use shared ada-idna and shared test dependencies.

--- src/unicode.cpp.orig
+++ src/unicode.cpp
@@ -5,9 +5,6 @@
 #include "ada/common_defs.h"
 #include "ada/log.h"
 
-ADA_PUSH_DISABLE_ALL_WARNINGS
-#include "ada_idna.cpp"
-ADA_POP_DISABLE_WARNINGS
 
 #include <algorithm>
 #include <array>
