$NetBSD$

Keep function declarations before definitions across linked input modules.
Preserve order inside each group and keep unresolved library imports.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
Source: Khronos SPIRV-Tools v2026.4,
commit ef96ed763b43b59b33b31b362f09a02b729fa1c9.
The upstream Apache-2.0 licence and authorship are unchanged.

--- source/link/linker.cpp.orig
+++ source/link/linker.cpp
@@ -401,11 +401,15 @@
     }
   }
 
-  // Process functions and their basic blocks
-  for (const auto& module : input_modules) {
-    for (const auto& func : *module) {
-      std::unique_ptr<opt::Function> cloned_func(func.Clone(linked_context));
-      linked_module->AddFunction(std::move(cloned_func));
+  // Keep declarations before definitions across module boundaries. Preserve
+  // the input order within each group, including unresolved library imports.
+  for (bool declarations : {true, false}) {
+    for (const auto& module : input_modules) {
+      for (const auto& func : *module) {
+        if ((func.begin() == func.end()) != declarations) continue;
+        std::unique_ptr<opt::Function> cloned_func(func.Clone(linked_context));
+        linked_module->AddFunction(std::move(cloned_func));
+      }
     }
   }
 
