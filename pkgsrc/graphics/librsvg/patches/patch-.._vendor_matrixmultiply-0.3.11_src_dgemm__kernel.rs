$NetBSD: patch-.._vendor_matrixmultiply-0.3.10_src_dgemm__kernel.rs,v 1.1 2025/12/08 12:40:15 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for matrixmultiply-0.3.11 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/matrixmultiply-0.3.11/src/dgemm_kernel.rs.orig
+++ ../vendor/matrixmultiply-0.3.11/src/dgemm_kernel.rs
@@ -32,7 +32,7 @@
 #[cfg(has_avx512)]
 struct KernelAvx512;
 
-#[cfg(target_arch="aarch64")]
+#[cfg(all(target_arch="aarch64", target_endian = "little"))]
 struct KernelNeon;
 
 struct KernelFallback;
@@ -62,7 +62,7 @@
         }
     }
 
-    #[cfg(target_arch="aarch64")]
+    #[cfg(all(target_arch="aarch64", target_endian = "little"))]
     {
         if is_aarch64_feature_detected_!("neon") {
             return selector.select(KernelNeon);
@@ -204,7 +204,7 @@
     }
 }
 
-#[cfg(target_arch="aarch64")]
+#[cfg(all(target_arch="aarch64", target_endian = "little"))]
 impl GemmKernel for KernelNeon {
     type Elem = T;
 
@@ -898,7 +898,7 @@
     }
 }
 
-#[cfg(target_arch="aarch64")]
+#[cfg(all(target_arch="aarch64", target_endian = "little"))]
 #[target_feature(enable="neon")]
 unsafe fn kernel_target_neon(k: usize, alpha: T, a: *const T, b: *const T,
                              beta: T, c: *mut T, rsc: isize, csc: isize)
@@ -1077,7 +1077,7 @@
         }
     }
 
-    #[cfg(any(target_arch="aarch64"))]
+    #[cfg(any(all(target_arch="aarch64", target_endian = "little")))]
     mod test_kernel_aarch64 {
         use super::test_a_kernel;
         use super::super::*;
