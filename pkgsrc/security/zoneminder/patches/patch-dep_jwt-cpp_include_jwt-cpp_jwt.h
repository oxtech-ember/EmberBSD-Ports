$NetBSD$

Use the common PicoJSON header and fix the external CMake target.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- dep/jwt-cpp/include/jwt-cpp/jwt.h.orig
+++ dep/jwt-cpp/include/jwt-cpp/jwt.h
@@ -5,7 +5,7 @@
 #ifndef PICOJSON_USE_INT64
 #define PICOJSON_USE_INT64
 #endif
-#include "picojson/picojson.h"
+#include <picojson.h>
 #endif
 
 #ifndef JWT_DISABLE_BASE64
