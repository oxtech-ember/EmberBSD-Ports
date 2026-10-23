$NetBSD$

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/i8x32_.rs.orig
+++ ../vendor/wide-1.7.1/src/i8x32_.rs
@@ -258,7 +258,7 @@
   #[inline]
   pub fn is_positive(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         // `neon` has dedicated greater-than-zero intrinsics.
         Self {
           a: self.a.is_positive(),
@@ -273,7 +273,7 @@
   #[inline]
   pub fn is_negative(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         // `neon` has dedicated less-than-zero intrinsics.
         Self {
           a: self.a.is_negative(),
