$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/starlark/crates/ffi/src/output_file.rs.orig
+++ src/gn/starlark/crates/ffi/src/output_file.rs
@@ -7,6 +7,6 @@
 impl OutputFile {
     /// Converts a GN OutputFile to a starlark File.
     pub fn to_rust(&self) -> types::File {
-        types::File::intern(self.value())
+        types::File::intern(crate::bridge::OutputFileValue(self))
     }
 }
