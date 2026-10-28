$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/starlark/crates/ffi/src/bridge.rs.orig
+++ src/gn/starlark/crates/ffi/src/bridge.rs
@@ -58,6 +58,7 @@
         // source code. It does not do anything on the rust side.
         include!("gn/err.h");
         include!("gn/ffi/err.h");
+        include!("gn/ffi/ports_adapters.h");
         include!("gn/ffi/scope.h");
         include!("gn/ffi/test_with_scope.h");
         include!("gn/ffi/value.h");
@@ -103,17 +104,14 @@
         pub(in crate::err) fn NewInputFile<'a, 'b>(name: &'a str, code: &'a str) -> &'b InputFile;
 
         type OutputFile;
-        #[cxx_return_type = "std::string_view"]
-        pub(in crate::output_file) fn value(self: &OutputFile) -> &str;
+        pub(in crate::output_file) fn OutputFileValue(value: &OutputFile) -> &str;
 
         type SourceDir;
-        #[cxx_return_type = "std::string_view"]
-        pub(in crate::label) fn SourceWithNoTrailingSlash(self: &SourceDir) -> &str;
+        pub(in crate::label) fn SourceDirValue(value: &SourceDir) -> &str;
 
         type Label;
         pub(in crate::label) fn dir(self: &Label) -> &SourceDir;
-        #[cxx_return_type = "const std::string&"]
-        pub fn name(self: &Label) -> &str;
+        pub(in crate::label) fn LabelName(value: &Label) -> &str;
 
         type Settings;
         pub(in crate::settings) fn toolchain_label(self: &Settings) -> &Label;
@@ -157,14 +155,10 @@
         #[allow(dead_code)]
         pub(in crate::value) fn NewValueForTesting() -> UniquePtr<Value>;
         pub(in crate::value) fn ValueSize() -> usize;
-        #[cxx_return_type = "Value::Type"]
-        #[cxx_name = "type"]
-        // We can't call this "type" in rust since it's a keyword.
-        pub(in crate::value) fn kind(self: &Value) -> ValueType;
+        pub(in crate::value) fn ValueKind(value: &Value) -> ValueType;
         pub(in crate::value) fn boolean_value(self: &Value) -> &bool;
         pub(in crate::value) fn int_value(self: &Value) -> &i64;
-        #[cxx_return_type = "const std::string&"]
-        pub(in crate::value) fn string_value(self: &Value) -> &str;
+        pub(in crate::value) fn ValueString(value: &Value) -> &str;
         #[cxx_name = "GetValueList"]
         pub(in crate::value) fn list_value_cxx(val: &Value) -> SliceAny;
         pub(in crate::value) fn scope_value(self: &Value) -> *const Scope;
