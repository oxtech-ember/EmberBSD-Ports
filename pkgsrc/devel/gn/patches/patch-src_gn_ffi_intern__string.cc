$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/ffi/intern_string.cc.orig
+++ src/gn/ffi/intern_string.cc
@@ -4,7 +4,7 @@
 
 #include <string_view>
 
-#include "cxx.h"
+#include "rust/cxx.h"
 #include "gn/string_atom.h"
 
 // `intern_string` is located in its own translation unit (`intern_string.cc`)
@@ -15,5 +15,6 @@
 // linker only pulls in this file and does not pull in `cxx_api.o`.
 extern "C" rust::Str intern_string(rust::Str s) {
   StringAtom atom(std::string_view{s});
-  return rust::Str(atom.str());
+  auto value = atom.str();
+  return rust::Str(value.data(), value.size());
 }
