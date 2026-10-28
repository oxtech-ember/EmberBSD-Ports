$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/starlark/crates/ffi/src/value.rs.orig
+++ src/gn/starlark/crates/ffi/src/value.rs
@@ -17,11 +17,11 @@
     }
 
     pub fn to_rust<'v>(&self, heap: &starlark::values::Heap<'v>) -> starlark::values::Value<'v> {
-        match self.kind() {
+        match crate::bridge::ValueKind(self) {
             ValueType::None => starlark::values::Value::new_none(),
             ValueType::Boolean => starlark::values::Value::new_bool(*self.boolean_value()),
             ValueType::Integer => heap.alloc(*self.int_value()),
-            ValueType::String => heap.alloc(self.string_value()),
+            ValueType::String => heap.alloc(crate::bridge::ValueString(self)),
             ValueType::List => {
                 let slice = self.list_value();
                 let items: Vec<_> = slice.iter().map(|item| item.to_rust(heap)).collect();
