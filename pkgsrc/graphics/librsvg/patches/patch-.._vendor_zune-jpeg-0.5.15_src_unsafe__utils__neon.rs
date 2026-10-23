$NetBSD: patch-.._vendor_zune-jpeg-0.5.13_src_unsafe__utils__neon.rs,v 1.1 2026/07/06 13:49:07 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for zune-jpeg-0.5.15 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/zune-jpeg-0.5.15/src/unsafe_utils_neon.rs.orig
+++ ../vendor/zune-jpeg-0.5.15/src/unsafe_utils_neon.rs
@@ -6,7 +6,7 @@
  * You can redistribute it or modify it under terms of the MIT, Apache License or Zlib license
  */
 
-#![cfg(all(feature = "neon", target_arch = "aarch64"))]
+#![cfg(all(feature = "neon", target_arch = "aarch64", target_endian = "little"))]
 // TODO can this be extended to armv7
 
 //! This module provides unsafe ways to do some things
