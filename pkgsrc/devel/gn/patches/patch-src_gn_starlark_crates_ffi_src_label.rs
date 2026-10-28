$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/starlark/crates/ffi/src/label.rs.orig
+++ src/gn/starlark/crates/ffi/src/label.rs
@@ -7,6 +7,11 @@
 use crate::{Label, SourceDir};
 
 impl Label {
+    /// Returns the borrowed GN label name.
+    pub fn name(&self) -> &str {
+        crate::bridge::LabelName(self)
+    }
+
     /// Returns the directory part of the label (the package path).
     pub fn package(&self) -> &PackageRef {
         self.dir().as_rust().unwrap()
@@ -20,7 +25,7 @@
 
 impl SourceDir {
     pub fn as_rust(&self) -> starlark::Result<&types::PackageRef> {
-        PackageRef::new(self.SourceWithNoTrailingSlash())
+        PackageRef::new(crate::bridge::SourceDirValue(self))
     }
 }
 
