$NetBSD$

Use the common PicoJSON header and fix the external CMake target.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- dep/jwt-cpp/include/jwt-cpp/traits/kazuho-picojson/traits.h.orig
+++ dep/jwt-cpp/include/jwt-cpp/traits/kazuho-picojson/traits.h
@@ -4,7 +4,7 @@
 #ifndef PICOJSON_USE_INT64
 #define PICOJSON_USE_INT64
 #endif
-#include "picojson/picojson.h"
+#include <picojson.h>
 
 #ifndef JWT_DISABLE_PICOJSON
 #define JWT_DISABLE_PICOJSON
