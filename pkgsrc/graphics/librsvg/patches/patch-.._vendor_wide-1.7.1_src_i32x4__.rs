$NetBSD: patch-.._vendor_wide-0.7.33_src_i32x4__.rs,v 1.1 2025/12/08 12:40:17 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/i32x4_.rs.orig
+++ ../vendor/wide-1.7.1/src/i32x4_.rs
@@ -37,7 +37,7 @@
     }
 
     impl Eq for i32x4 { }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
     use core::arch::aarch64::*;
 
     /// A SIMD vector with four elements of type [`i32`].
@@ -100,7 +100,7 @@
         Self { sse: cmp_lt_mask_i32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i32x4_lt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_s32_u32(vcltq_s32(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -120,7 +120,7 @@
         Self { sse: cmp_gt_mask_i32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i32x4_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_s32_u32(vcgtq_s32(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -140,7 +140,7 @@
         !self.simd_gt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i32x4_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_gt(rhs)
       } else {
         Self { arr: [
@@ -160,7 +160,7 @@
         !self.simd_lt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i32x4_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_lt(rhs)
       } else {
         Self { arr: [
@@ -180,7 +180,7 @@
         // mask the shift count to 31 to have same behavior on all platforms
         let shift_by = bitand_m128i(rhs.sse, set_splat_i32_m128i(31));
         Self { sse: shr_each_i32_m128i(self.sse, shift_by) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // mask the shift count to 31 to have same behavior on all platforms
           // no right shift, have to pass negative value to left shift on neon
@@ -210,7 +210,7 @@
         Self { sse: shr_all_i32_m128i(self.sse, shift) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i32x4_shr(self.simd, rhs) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Use `rhs % 32` to perform wrapping shift and not unbounded shift.
         #[expect(clippy::suspicious_arithmetic_impl)]
         unsafe {Self { neon: vshlq_s32(self.neon, vmovq_n_s32( -(rhs as i32 & 31))) }}
@@ -232,7 +232,7 @@
         Self { sse: max_i32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i32x4_max(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_s32(self.neon, rhs.neon) }}
       } else {
         self.simd_lt(rhs).select(rhs, self)
@@ -247,7 +247,7 @@
         Self { sse: min_i32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i32x4_min(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminq_s32(self.neon, rhs.neon) }}
       } else {
         self.simd_lt(rhs).select(self, rhs)
@@ -272,7 +272,7 @@
     pick! {
       if #[cfg(target_feature="avx2")] {
         Self { sse: shr_each_i32_m128i(self.sse, rhs.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -299,7 +299,7 @@
         Self { sse: shr_all_i32_m128i(self.sse, cast([rhs as u64, 0])) }
       } else if #[cfg(target_feature="simd128")] {
         if rhs < 32 { Self { simd: i32x4_shr(self.simd, rhs) } } else { self.is_negative() }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -328,7 +328,7 @@
 
         // If overflow occurs return `MAX` if positive or `MIN` if negative.
         overflow.select(Self::MAX ^ negative, result)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqaddq_s32(self.neon, rhs.neon) } }
       } else {
         Self {
@@ -353,7 +353,7 @@
 
         // If overflow occurs return `MAX` if positive or `MIN` if negative.
         overflow.select(Self::MAX ^ negative, result)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqsubq_s32(self.neon, rhs.neon) } }
       } else {
         Self {
@@ -401,7 +401,7 @@
               a: i64x2 { simd: i64x2_extmul_low_i32x4(self.simd, rhs.simd) },
               b: i64x2 { simd: i64x2_extmul_high_i32x4(self.simd, rhs.simd) },
             }
-        } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+        } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
           unsafe {
             i64x4 { a: i64x2 { neon: vmull_s32(vget_low_s32(self.neon), vget_low_s32(rhs.neon)) },
                     b: i64x2 { neon: vmull_s32(vget_high_s32(self.neon), vget_high_s32(rhs.neon)) } }
@@ -445,7 +445,7 @@
           u32x4 { simd: i32x4_shuffle::<0, 2, 4, 6>(low_wide_mul, high_wide_mul) },
           i32x4 { simd: i32x4_shuffle::<1, 3, 5, 7>(low_wide_mul, high_wide_mul) },
         )
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_s32_s64(
             vmull_s32(vget_low_s32(self.neon), vget_low_s32(rhs.neon)),
@@ -510,7 +510,7 @@
         let high_wide_mul = i64x2_extmul_high_i32x4(self.simd, rhs.simd);
 
         Self { simd: i32x4_shuffle::<1, 3, 5, 7>(low_wide_mul, high_wide_mul) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_s32_s64(
             vmull_s32(vget_low_s32(self.neon), vget_low_s32(rhs.neon)),
@@ -542,7 +542,7 @@
         Self { sse: abs_i32_m128i(self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i32x4_abs(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vabsq_s32(self.neon) }}
       } else {
         let arr: [i32; 4] = cast(self);
@@ -559,7 +559,7 @@
   #[inline]
   pub fn is_positive(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vreinterpretq_s32_u32(vcgtzq_s32(self.neon)) } }
       } else {
         self.simd_gt(Self::ZERO)
@@ -570,7 +570,7 @@
   #[inline]
   pub fn is_negative(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vreinterpretq_s32_u32(vcltzq_s32(self.neon)) } }
       } else {
         self.simd_lt(Self::ZERO)
@@ -593,7 +593,7 @@
         cast(convert_to_m128_from_i32_m128i(self.sse))
       } else if #[cfg(target_feature="simd128")] {
         cast(Self { simd: f32x4_convert_i32x4(self.simd) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         cast(unsafe {Self { neon: vreinterpretq_s32_f32(vcvtq_f32_s32(self.neon)) }})
       } else {
         let arr: [i32; 4] = cast(self);
