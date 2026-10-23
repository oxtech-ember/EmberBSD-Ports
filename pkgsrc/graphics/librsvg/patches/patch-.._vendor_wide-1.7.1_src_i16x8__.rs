$NetBSD: patch-.._vendor_wide-0.7.33_src_i16x8__.rs,v 1.1 2025/12/08 12:40:16 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/i16x8_.rs.orig
+++ ../vendor/wide-1.7.1/src/i16x8_.rs
@@ -37,7 +37,7 @@
     }
 
     impl Eq for i16x8 { }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
     use core::arch::aarch64::*;
 
     /// A SIMD vector with eight elements of type [`i16`].
@@ -100,7 +100,7 @@
         Self { sse: cmp_lt_mask_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_lt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_s16_u16(vcltq_s16(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -124,7 +124,7 @@
         Self { sse: cmp_gt_mask_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_s16_u16(vcgtq_s16(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -148,7 +148,7 @@
         !self.simd_gt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_gt(rhs)
       } else {
         Self { arr: [
@@ -172,7 +172,7 @@
         !self.simd_lt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_lt(rhs)
       } else {
         Self { arr: [
@@ -202,7 +202,7 @@
         let rhs = bitand_m128i(rhs.sse, set_splat_i16_m128i(15));
         // TODO(safe_arch): Add `_mm_srav_epi16`.
         cast(unsafe { _mm_srav_epi16(self.sse.0, rhs.0) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Mask `rhs` to 15 to match `wrapping_shr`, and negate it because
           // there is no shift-right intrinsic.
@@ -237,7 +237,7 @@
         Self { sse: shr_all_i16_m128i(self.sse, shift) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_shr(self.simd, rhs) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Use `rhs % 16` to perform wrapping shift and not unbounded shift.
         #[expect(clippy::suspicious_arithmetic_impl)]
         unsafe {Self { neon: vshlq_s16(self.neon, vmovq_n_s16( -(rhs as i16 & 15))) }}
@@ -263,7 +263,7 @@
         Self { sse: max_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_max(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_s16(self.neon, rhs.neon) }}
       } else {
         self.simd_lt(rhs).select(rhs, self)
@@ -278,7 +278,7 @@
         Self { sse: min_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_min(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminq_s16(self.neon, rhs.neon) }}
       } else {
         self.simd_lt(rhs).select(self, rhs)
@@ -297,7 +297,7 @@
           let lo16 = shr_imm_u32_m128i::<16>(sum32);
           let sum16 = max_i16_m128i(sum32, lo16);
           extract_i16_as_i32_m128i::<0>(sum16) as i16
-        } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+        } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
           unsafe { vmaxvq_s16(self.neon) }
         } else {
         let arr: [i16; 8] = cast(self);
@@ -326,7 +326,7 @@
           let lo16 = shr_imm_u32_m128i::<16>(sum32);
           let sum16 = min_i16_m128i(sum32, lo16);
           extract_i16_as_i32_m128i::<0>(sum16) as i16
-        } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+        } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
           unsafe { vminvq_s16(self.neon) }
         } else {
         let arr: [i16; 8] = cast(self);
@@ -355,7 +355,7 @@
 
         // TODO(safe_arch): Add `_mm_srav_epi16`.
         cast(unsafe { _mm_srav_epi16(self.sse.0, rhs.sse.0) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -386,7 +386,7 @@
         Self { sse: shr_all_i16_m128i(self.sse, cast([rhs as u64, 0])) }
       } else if #[cfg(target_feature="simd128")] {
         if rhs < 16 { Self { simd: i16x8_shr(self.simd, rhs) } } else { self.is_negative() }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -416,7 +416,7 @@
         Self { sse: add_saturating_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_add_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vqaddq_s16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -440,7 +440,7 @@
         Self { sse: sub_saturating_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_sub_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqsubq_s16(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -481,7 +481,7 @@
             a: i32x4 { sse:unpack_low_i16_m128i(low, high) },
             b: i32x4 { sse:unpack_high_i16_m128i(low, high) }
           }
-        } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+        } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
           let lhs_low = unsafe { vget_low_s16(self.neon) };
           let rhs_low = unsafe { vget_low_s16(rhs.neon) };
 
@@ -521,7 +521,7 @@
           u16x8 { simd: i16x8_shuffle::<0, 2, 4, 6, 8, 10, 12, 14>(low_wide_mul, high_wide_mul) },
           i16x8 { simd: i16x8_shuffle::<1, 3, 5, 7, 9, 11, 13, 15>(low_wide_mul, high_wide_mul) },
         )
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_s16_s32(
             vmull_s16(vget_low_s16(self.neon), vget_low_s16(rhs.neon)),
@@ -584,7 +584,7 @@
     pick! {
       if #[cfg(target_feature="sse2")] {
         Self { sse: mul_i16_keep_high_m128i(self.sse, rhs.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         let lhs_low = unsafe { vget_low_s16(self.neon) };
         let rhs_low = unsafe { vget_low_s16(rhs.neon) };
 
@@ -632,7 +632,7 @@
         Self { sse: abs_i16_m128i(self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_abs(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vabsq_s16(self.neon) }}
       } else {
         let arr: [i16; 8] = cast(self);
@@ -654,7 +654,7 @@
   #[inline]
   pub fn is_positive(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vreinterpretq_s16_u16(vcgtzq_s16(self.neon)) } }
       } else {
         self.simd_gt(Self::ZERO)
@@ -665,7 +665,7 @@
   #[inline]
   pub fn is_negative(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vreinterpretq_s16_u16(vcltzq_s16(self.neon)) } }
       } else {
         self.simd_lt(Self::ZERO)
@@ -741,7 +741,7 @@
         use core::arch::wasm32::*;
 
         i16x8 { simd: i16x8_narrow_i32x4(v.a.simd, v.b.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         use core::arch::aarch64::*;
 
         unsafe {
@@ -819,7 +819,7 @@
         unsafe { Self { sse: load_unaligned_m128i( &*(input.as_ptr() as * const [u8;16]) ) } }
       } else if #[cfg(target_feature="simd128")] {
         unsafe { Self { simd: v128_load(input.as_ptr() as *const v128 ) } }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vld1q_s16( input.as_ptr() as *const i16 ) } }
       } else {
         // 2018 edition doesn't have try_into
@@ -841,7 +841,7 @@
         i32x4 { sse:  mul_i16_horizontal_add_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         i32x4 { simd: i32x4_dot_i16x8(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           let pl = vmull_s16(vget_low_s16(self.neon),  vget_low_s16(rhs.neon));
           let ph = vmull_high_s16(self.neon, rhs.neon);
@@ -884,7 +884,7 @@
         Self { sse: s }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_q15mulr_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqrdmulhq_s16(self.neon, rhs.neon) } }
       } else {
         // compiler does a surprisingly good job of vectorizing this
@@ -929,7 +929,7 @@
         Self { sse: s }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i16x8_q15mulr_sat(self.simd, i16x8_splat(rhs)) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqrdmulhq_n_s16(self.neon, rhs) } }
       } else {
         // compiler does a surprisingly good job of vectorizing this
