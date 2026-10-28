$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/ffi/scope.cc.orig
+++ src/gn/ffi/scope.cc
@@ -73,7 +73,8 @@
 SliceAny GetScopeItems(const Scope& scope) {
   auto range =
       scope.GetCurrentScopeValues() | std::views::transform([](auto pair) {
-        return KeyValue{rust::Str(pair.first), *pair.second};
+        auto key = std::string_view(pair.first);
+        return KeyValue{rust::Str(key.data(), key.size()), *pair.second};
       });
   return IntoSlice(to_vec(range));
 }
