$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/ffi/scope.h.orig
+++ src/gn/ffi/scope.h
@@ -7,7 +7,7 @@
 
 #include <memory>
 
-#include "cxx.h"
+#include "rust/cxx.h"
 
 struct ParseNodePtr;
 class Scope;
