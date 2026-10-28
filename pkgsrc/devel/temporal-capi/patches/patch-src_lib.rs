$NetBSD$

Link the native standard allocator and panic runtime into the shared C API.
Origin: EmberBSD (AI-assisted).

--- src/lib.rs.orig
+++ src/lib.rs
@@ -19,6 +19,8 @@
     forbid(clippy::unwrap_used, clippy::expect_used, clippy::indexing_slicing)
 )]
 
+// The shared C ABI needs the standard allocator and panic runtime.
+extern crate std;
 extern crate alloc;
 
 #[macro_use]
