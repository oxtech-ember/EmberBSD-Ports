$NetBSD: patch-.._vendor_memchr-2.8.0_src_arch_aarch64_mod.rs,v 1.1 2026/07/06 13:49:07 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for memchr-2.8.3 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/memchr-2.8.3/src/arch/aarch64/mod.rs.orig
+++ ../vendor/memchr-2.8.3/src/arch/aarch64/mod.rs
@@ -2,6 +2,8 @@
 Vector algorithms for the `aarch64` target.
 */
 
+#[cfg(target_endian = "little")]
 pub mod neon;
 
+#[cfg(target_endian = "little")]
 pub(crate) mod memchr;
