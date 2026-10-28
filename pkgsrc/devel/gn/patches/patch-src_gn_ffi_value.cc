$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/ffi/value.cc.orig
+++ src/gn/ffi/value.cc
@@ -10,11 +10,16 @@
 #include "gn/ffi/bridge.h"
 #include "gn/ffi/slice.h"
 
-namespace rust {
-ValueType cxx_to_rust(Value::Type t) {
-  return static_cast<ValueType>(t);
+static_assert(static_cast<uint8_t>(Value::NONE) == static_cast<uint8_t>(ValueType::None));
+static_assert(static_cast<uint8_t>(Value::BOOLEAN) == static_cast<uint8_t>(ValueType::Boolean));
+static_assert(static_cast<uint8_t>(Value::INTEGER) == static_cast<uint8_t>(ValueType::Integer));
+static_assert(static_cast<uint8_t>(Value::STRING) == static_cast<uint8_t>(ValueType::String));
+static_assert(static_cast<uint8_t>(Value::LIST) == static_cast<uint8_t>(ValueType::List));
+static_assert(static_cast<uint8_t>(Value::SCOPE) == static_cast<uint8_t>(ValueType::Scope));
+
+ValueType ValueKind(const Value& value) {
+  return static_cast<ValueType>(value.type());
 }
-}  // namespace rust
 
 size_t ValueSize() {
   return sizeof(Value);
