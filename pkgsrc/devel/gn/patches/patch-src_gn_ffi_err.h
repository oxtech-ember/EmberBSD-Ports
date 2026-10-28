$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/ffi/err.h.orig
+++ src/gn/ffi/err.h
@@ -9,7 +9,7 @@
 #include <string>
 #include <vector>
 
-#include "cxx.h"
+#include "rust/cxx.h"
 #include "gn/err.h"
 #include "gn/input_file.h"
 #include "gn/input_file_manager.h"
