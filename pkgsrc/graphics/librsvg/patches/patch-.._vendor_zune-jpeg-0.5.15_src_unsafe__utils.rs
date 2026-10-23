$NetBSD: patch-.._vendor_zune-jpeg-0.5.13_src_unsafe__utils.rs,v 1.1 2026/07/06 13:49:07 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for zune-jpeg-0.5.15 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/zune-jpeg-0.5.15/src/unsafe_utils.rs.orig
+++ ../vendor/zune-jpeg-0.5.15/src/unsafe_utils.rs
@@ -1,4 +1,4 @@
 #[cfg(all(feature = "x86", any(target_arch = "x86", target_arch = "x86_64")))]
 pub use crate::unsafe_utils_avx2::*;
-#[cfg(all(feature = "neon", target_arch = "aarch64"))]
+#[cfg(all(feature = "neon", target_arch = "aarch64", target_endian = "little"))]
 pub use crate::unsafe_utils_neon::*;
