$NetBSD: patch-.._vendor_matrixmultiply-0.3.10_src_sgemm__kernel.rs,v 1.1 2025/12/08 12:40:15 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for matrixmultiply-0.3.11 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/matrixmultiply-0.3.11/src/sgemm_kernel.rs.orig
+++ ../vendor/matrixmultiply-0.3.11/src/sgemm_kernel.rs
@@ -11,7 +11,7 @@
 use crate::kernel::{U4, U8};
 #[cfg(has_avx512)]
 use crate::kernel::U16;
-#[cfg(any(target_arch="x86", target_arch="x86_64", target_arch="aarch64", target_arch="wasm32"))]
+#[cfg(any(target_arch="x86", target_arch="x86_64", all(target_arch="aarch64", target_endian = "little"), target_arch="wasm32"))]
 use crate::kernel_util::preferential_transpose;
 use crate::kernel_util::at;
 use crate::archparam;
@@ -33,7 +33,7 @@
 #[cfg(has_avx512)]
 struct KernelAvx512;
 
-#[cfg(target_arch="aarch64")]
+#[cfg(all(target_arch="aarch64", target_endian = "little"))]
 struct KernelNeon;
 #[cfg(all(target_arch="wasm32", target_feature="simd128"))]
 struct KernelWasmSimd;
@@ -63,7 +63,7 @@
             return selector.select(KernelAvx);
         }
     }
-    #[cfg(target_arch="aarch64")]
+    #[cfg(all(target_arch="aarch64", target_endian = "little"))]
     {
         if is_aarch64_feature_detected_!("neon") {
             return selector.select(KernelNeon);
@@ -201,7 +201,7 @@
     }
 }
 
-#[cfg(target_arch="aarch64")]
+#[cfg(all(target_arch="aarch64", target_endian = "little"))]
 impl GemmKernel for KernelNeon {
     type Elem = T;
 
@@ -556,7 +556,7 @@
     }
 }
 
-#[cfg(target_arch="aarch64")]
+#[cfg(all(target_arch="aarch64", target_endian = "little"))]
 #[target_feature(enable="neon")]
 unsafe fn kernel_target_neon(k: usize, alpha: T, a: *const T, b: *const T,
                              beta: T, c: *mut T, rsc: isize, csc: isize)
@@ -888,7 +888,7 @@
         }
     }
 
-    #[cfg(any(target_arch="aarch64"))]
+    #[cfg(any(all(target_arch="aarch64", target_endian = "little")))]
     mod test_kernel_aarch64 {
         use super::test_a_kernel;
         use super::super::*;
