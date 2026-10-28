$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/ffi/value.h.orig
+++ src/gn/ffi/value.h
@@ -7,7 +7,7 @@
 
 #include <memory>
 
-#include "cxx.h"
+#include "rust/cxx.h"
 #include "gn/value.h"
 
 class Scope;
