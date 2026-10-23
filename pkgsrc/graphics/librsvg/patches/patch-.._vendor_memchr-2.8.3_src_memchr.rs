$NetBSD: patch-.._vendor_memchr-2.8.0_src_memchr.rs,v 1.1 2026/07/06 13:49:07 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for memchr-2.8.3 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/memchr-2.8.3/src/memchr.rs.orig
+++ ../vendor/memchr-2.8.3/src/memchr.rs
@@ -518,14 +518,14 @@
     {
         crate::arch::wasm32::memchr::memchr_raw(needle, start, end)
     }
-    #[cfg(target_arch = "aarch64")]
+    #[cfg(all(target_arch = "aarch64", target_endian = "little"))]
     {
         crate::arch::aarch64::memchr::memchr_raw(needle, start, end)
     }
     #[cfg(not(any(
         target_arch = "x86_64",
         all(target_arch = "wasm32", target_feature = "simd128"),
-        target_arch = "aarch64"
+        all(target_arch = "aarch64", target_endian = "little")
     )))]
     {
         crate::arch::all::memchr::One::new(needle).find_raw(start, end)
@@ -551,14 +551,14 @@
     {
         crate::arch::wasm32::memchr::memrchr_raw(needle, start, end)
     }
-    #[cfg(target_arch = "aarch64")]
+    #[cfg(all(target_arch = "aarch64", target_endian = "little"))]
     {
         crate::arch::aarch64::memchr::memrchr_raw(needle, start, end)
     }
     #[cfg(not(any(
         target_arch = "x86_64",
         all(target_arch = "wasm32", target_feature = "simd128"),
-        target_arch = "aarch64"
+        all(target_arch = "aarch64", target_endian = "little")
     )))]
     {
         crate::arch::all::memchr::One::new(needle).rfind_raw(start, end)
@@ -585,14 +585,14 @@
     {
         crate::arch::wasm32::memchr::memchr2_raw(needle1, needle2, start, end)
     }
-    #[cfg(target_arch = "aarch64")]
+    #[cfg(all(target_arch = "aarch64", target_endian = "little"))]
     {
         crate::arch::aarch64::memchr::memchr2_raw(needle1, needle2, start, end)
     }
     #[cfg(not(any(
         target_arch = "x86_64",
         all(target_arch = "wasm32", target_feature = "simd128"),
-        target_arch = "aarch64"
+        all(target_arch = "aarch64", target_endian = "little")
     )))]
     {
         crate::arch::all::memchr::Two::new(needle1, needle2)
@@ -620,7 +620,7 @@
     {
         crate::arch::wasm32::memchr::memrchr2_raw(needle1, needle2, start, end)
     }
-    #[cfg(target_arch = "aarch64")]
+    #[cfg(all(target_arch = "aarch64", target_endian = "little"))]
     {
         crate::arch::aarch64::memchr::memrchr2_raw(
             needle1, needle2, start, end,
@@ -629,7 +629,7 @@
     #[cfg(not(any(
         target_arch = "x86_64",
         all(target_arch = "wasm32", target_feature = "simd128"),
-        target_arch = "aarch64"
+        all(target_arch = "aarch64", target_endian = "little")
     )))]
     {
         crate::arch::all::memchr::Two::new(needle1, needle2)
@@ -662,7 +662,7 @@
             needle1, needle2, needle3, start, end,
         )
     }
-    #[cfg(target_arch = "aarch64")]
+    #[cfg(all(target_arch = "aarch64", target_endian = "little"))]
     {
         crate::arch::aarch64::memchr::memchr3_raw(
             needle1, needle2, needle3, start, end,
@@ -671,7 +671,7 @@
     #[cfg(not(any(
         target_arch = "x86_64",
         all(target_arch = "wasm32", target_feature = "simd128"),
-        target_arch = "aarch64"
+        all(target_arch = "aarch64", target_endian = "little")
     )))]
     {
         crate::arch::all::memchr::Three::new(needle1, needle2, needle3)
@@ -704,7 +704,7 @@
             needle1, needle2, needle3, start, end,
         )
     }
-    #[cfg(target_arch = "aarch64")]
+    #[cfg(all(target_arch = "aarch64", target_endian = "little"))]
     {
         crate::arch::aarch64::memchr::memrchr3_raw(
             needle1, needle2, needle3, start, end,
@@ -713,7 +713,7 @@
     #[cfg(not(any(
         target_arch = "x86_64",
         all(target_arch = "wasm32", target_feature = "simd128"),
-        target_arch = "aarch64"
+        all(target_arch = "aarch64", target_endian = "little")
     )))]
     {
         crate::arch::all::memchr::Three::new(needle1, needle2, needle3)
@@ -736,14 +736,14 @@
     {
         crate::arch::wasm32::memchr::count_raw(needle, start, end)
     }
-    #[cfg(target_arch = "aarch64")]
+    #[cfg(all(target_arch = "aarch64", target_endian = "little"))]
     {
         crate::arch::aarch64::memchr::count_raw(needle, start, end)
     }
     #[cfg(not(any(
         target_arch = "x86_64",
         all(target_arch = "wasm32", target_feature = "simd128"),
-        target_arch = "aarch64"
+        all(target_arch = "aarch64", target_endian = "little")
     )))]
     {
         crate::arch::all::memchr::One::new(needle).count_raw(start, end)
