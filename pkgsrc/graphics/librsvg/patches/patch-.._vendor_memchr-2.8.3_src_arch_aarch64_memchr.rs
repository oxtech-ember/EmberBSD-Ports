$NetBSD: patch-.._vendor_memchr-2.8.0_src_arch_aarch64_memchr.rs,v 1.1 2026/07/06 13:49:07 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for memchr-2.8.3 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/memchr-2.8.3/src/arch/aarch64/memchr.rs.orig
+++ ../vendor/memchr-2.8.3/src/arch/aarch64/memchr.rs
@@ -8,7 +8,7 @@
 
 macro_rules! defraw {
     ($ty:ident, $find:ident, $start:ident, $end:ident, $($needles:ident),+) => {{
-        #[cfg(target_feature = "neon")]
+        #[cfg(all(target_feature = "neon", target_endian = "little"))]
         {
             use crate::arch::aarch64::neon::memchr::$ty;
 
@@ -19,7 +19,7 @@
             // enabled.
             $ty::new_unchecked($($needles),+).$find($start, $end)
         }
-        #[cfg(not(target_feature = "neon"))]
+        #[cfg(not(all(target_feature = "neon", target_endian = "little")))]
         {
             use crate::arch::all::memchr::$ty;
 
