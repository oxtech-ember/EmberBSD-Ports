# $NetBSD$

Use shared ada-idna and shared test dependencies.

--- include/ada/unicode.h.orig
+++ include/ada/unicode.h
@@ -6,7 +6,7 @@
 #define ADA_UNICODE_H
 
 #include "ada/common_defs.h"
-#include "ada/ada_idna.h"
+#include <idna.h>
 
 #include <string>
 #include <string_view>
