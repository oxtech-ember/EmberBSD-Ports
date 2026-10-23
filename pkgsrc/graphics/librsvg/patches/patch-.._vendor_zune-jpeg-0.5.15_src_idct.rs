$NetBSD: patch-.._vendor_zune-jpeg-0.5.13_src_idct.rs,v 1.1 2026/07/06 13:49:07 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for zune-jpeg-0.5.15 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/zune-jpeg-0.5.15/src/idct.rs.orig
+++ ../vendor/zune-jpeg-0.5.15/src/idct.rs
@@ -41,7 +41,7 @@
 
 #[cfg(feature = "x86")]
 pub mod avx2;
-#[cfg(feature = "neon")]
+#[cfg(all(feature = "neon", target_endian = "little"))]
 pub mod neon;
 
 pub mod scalar;
@@ -60,7 +60,7 @@
             };
         }
     }
-    #[cfg(target_arch = "aarch64")]
+    #[cfg(all(target_arch = "aarch64", target_endian = "little"))]
     #[cfg(feature = "neon")]
     {
         if options.use_neon() {
