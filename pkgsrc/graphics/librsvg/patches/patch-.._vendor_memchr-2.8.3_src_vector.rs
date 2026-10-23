$NetBSD: patch-.._vendor_memchr-2.8.0_src_vector.rs,v 1.1 2026/07/06 13:49:07 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for memchr-2.8.3 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/memchr-2.8.3/src/vector.rs.orig
+++ ../vendor/memchr-2.8.3/src/vector.rs
@@ -289,7 +289,7 @@
     }
 }
 
-#[cfg(target_arch = "aarch64")]
+#[cfg(all(target_arch = "aarch64", target_endian = "little"))]
 mod aarch64neon {
     use core::arch::aarch64::*;
 
