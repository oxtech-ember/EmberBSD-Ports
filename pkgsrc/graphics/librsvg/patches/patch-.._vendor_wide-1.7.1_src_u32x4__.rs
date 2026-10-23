$NetBSD: patch-.._vendor_wide-0.7.33_src_u32x4__.rs,v 1.1 2025/12/08 12:40:17 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/u32x4_.rs.orig
+++ ../vendor/wide-1.7.1/src/u32x4_.rs
@@ -37,7 +37,7 @@
     }
 
     impl Eq for u32x4 { }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
     use core::arch::aarch64::*;
 
     /// A SIMD vector with four elements of type [`u32`].
@@ -104,7 +104,7 @@
         Self { sse: add_i32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_add(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vaddq_u32(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -124,7 +124,7 @@
         Self { sse: sub_i32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_sub(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vsubq_u32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -144,7 +144,7 @@
         Self { sse: mul_32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_mul(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmulq_u32(self.neon, rhs.neon) }}
       } else {
         let arr1: [u32; 4] = cast(self);
@@ -166,7 +166,7 @@
         Self { sse: bitand_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_and(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vandq_u32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -186,7 +186,7 @@
         Self { sse: bitor_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_or(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vorrq_u32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -206,7 +206,7 @@
         Self { sse: bitxor_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_xor(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: veorq_u32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -226,7 +226,7 @@
         Self { sse: cmp_eq_mask_i32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_eq(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vceqq_u32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -246,7 +246,7 @@
         !self.simd_eq(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_ne(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_eq(rhs)
       } else {
         Self { arr: [
@@ -274,7 +274,7 @@
         Self { sse: cmp_gt_mask_i32_m128i((self ^ h).sse, (rhs ^ h).sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {Self { neon: vcgtq_u32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -294,7 +294,7 @@
         !self.simd_gt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_gt(rhs)
       } else {
         Self { arr: [
@@ -314,7 +314,7 @@
         !self.simd_lt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_lt(rhs)
       } else {
         Self { arr: [
@@ -359,7 +359,7 @@
         let high_32 = u32x4_shuffle::<1, 0, 0, 0>(reduce_64, reduce_64);
         let reduce_32 = u32x4_mul(reduce_64, high_32);
         u32x4_extract_lane::<0>(reduce_32)
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let high_64 = vextq_u32::<2>(self.neon, self.neon);
           let reduce_64 = vmulq_u32(self.neon, high_64);
@@ -386,7 +386,7 @@
         }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_one.simd, if_zero.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_u32(self.neon, if_one.neon, if_zero.neon) }}
       } else {
         generic_bit_blend(self, if_one, if_zero)
@@ -401,7 +401,7 @@
         Self { sse: blend_varying_i8_m128i(if_false.sse, if_true.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_true.simd, if_false.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_u32(self.neon, if_true.neon, if_false.neon) }}
       } else {
         generic_bit_blend(self, if_true, if_false)
@@ -417,7 +417,7 @@
         move_mask_m128(cast(self.sse)) as u32
       } else if #[cfg(target_feature="simd128")] {
         u32x4_bitmask(self.simd) as u32
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe
         {
           // set all to 1 if top bit is set, else 0
@@ -447,7 +447,7 @@
         move_mask_m128(cast(self.sse)) != 0
       } else if #[cfg(target_feature="simd128")] {
         u32x4_bitmask(self.simd) != 0
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         // some lanes are negative
         unsafe {
           vminvq_s32(self.cast_signed().neon) < 0
@@ -467,7 +467,7 @@
         move_mask_m128(cast(self.sse)) == 0b1111
       } else if #[cfg(target_feature="simd128")] {
         u32x4_bitmask(self.simd) == 0b1111
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // all lanes are negative
         unsafe {
           vmaxvq_s32(self.cast_signed().neon) < 0
@@ -654,7 +654,7 @@
         // mask the shift count to 31 to have same behavior on all platforms
         let shift_by = bitand_m128i(rhs.sse, set_splat_i32_m128i(31));
         Self { sse: shl_each_u32_m128i(self.sse, shift_by) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // mask the shift count to 31 to have same behavior on all platforms
           let shift_by = vreinterpretq_s32_u32(vandq_u32(rhs.neon, vmovq_n_u32(31)));
@@ -683,7 +683,7 @@
         Self { sse: shl_all_u32_m128i(self.sse, shift) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_shl(self.simd, rhs) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Use `rhs % 32` to perform wrapping shift and not unbounded shift.
         #[expect(clippy::suspicious_arithmetic_impl)]
         unsafe {Self { neon: vshlq_u32(self.neon, vmovq_n_s32(rhs as i32 & 31)) }}
@@ -705,7 +705,7 @@
         // mask the shift count to 31 to have same behavior on all platforms
         let shift_by = bitand_m128i(rhs.sse, set_splat_i32_m128i(31));
         Self { sse: shr_each_u32_m128i(self.sse, shift_by) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // mask the shift count to 31 to have same behavior on all platforms
           // no right shift, have to pass negative value to left shift on neon
@@ -735,7 +735,7 @@
         Self { sse: shr_all_u32_m128i(self.sse, shift) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_shr(self.simd, rhs) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Use `rhs % 32` to perform wrapping shift and not unbounded shift.
         #[expect(clippy::suspicious_arithmetic_impl)]
         unsafe {Self { neon: vshlq_u32(self.neon, vmovq_n_s32( -(rhs as i32 & 31))) }}
@@ -757,9 +757,9 @@
         Self { sse: max_u32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_max(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_u32(self.neon, rhs.neon) }}
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_u16(self.neon, rhs.neon) }}
       } else {
         let arr: [u32; 4] = cast(self);
@@ -781,7 +781,7 @@
         Self { sse: min_u32_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_min(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminq_u32(self.neon, rhs.neon) }}
       } else {
         let arr: [u32; 4] = cast(self);
@@ -813,7 +813,7 @@
     pick! {
       if #[cfg(target_feature="avx2")] {
         Self { sse: shl_each_u32_m128i(self.sse, rhs.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // The intrinsic has different semantics so we need to mask ourselves.
           Self { neon: vshlq_u32(self.neon, vreinterpretq_s32_u32(rhs.neon)) } & rhs.simd_lt(32)
@@ -840,7 +840,7 @@
       } else if #[cfg(target_feature="simd128")] {
         // The intrinsic performs wrapping shift so we need to mask the result.
         Self { simd: u32x4_shl(self.simd, rhs) } & Self::splat(rhs).simd_lt(32)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // The intrinsic has different semantics so we need to saturate `rhs`.
         unsafe { Self { neon: vshlq_u32(self.neon, vmovq_n_s32(rhs.min(32) as i32)) } }
       } else {
@@ -859,7 +859,7 @@
     pick! {
       if #[cfg(target_feature="avx2")] {
         Self { sse: shr_each_u32_m128i(self.sse, rhs.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // mask to hide `rhs` overflow.
@@ -886,7 +886,7 @@
         Self { sse: shr_all_u32_m128i(self.sse, cast([rhs as u64, 0])) }
       } else if #[cfg(target_feature="simd128")] {
         if rhs < 32 { Self { simd: u32x4_shr(self.simd, rhs) } } else { Self::ZERO }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -913,7 +913,7 @@
         let overflow = result.simd_lt(self);
         // Return `MAX` (all bits set) if overflow occurs.
         result | overflow
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqaddq_u32(self.neon, rhs.neon) } }
       } else {
         Self {
@@ -936,7 +936,7 @@
         let no_overflow = result.simd_le(self);
         // Return `0` (no bits set) if overflow occurs.
         result & no_overflow
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqsubq_u32(self.neon, rhs.neon) } }
       } else {
         Self {
@@ -983,7 +983,7 @@
             a: u64x2 { simd: u64x2_extmul_low_u32x4(self.simd, rhs.simd) },
             b: u64x2 { simd: u64x2_extmul_high_u32x4(self.simd, rhs.simd) },
           }
-        } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+        } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           u64x4 { a: u64x2 { neon: vmull_u32(vget_low_u32(self.neon), vget_low_u32(rhs.neon)) },
                   b: u64x2 { neon: vmull_u32(vget_high_u32(self.neon), vget_high_u32(rhs.neon)) } }
@@ -1025,7 +1025,7 @@
           Self { simd: u32x4_shuffle::<0, 2, 4, 6>(low_wide_mul, high_wide_mul) },
           Self { simd: u32x4_shuffle::<1, 3, 5, 7>(low_wide_mul, high_wide_mul) },
         )
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_u32_u64(
             vmull_u32(vget_low_u32(self.neon), vget_low_u32(rhs.neon)),
@@ -1099,7 +1099,7 @@
         let high = u64x2_extmul_high_u32x4(self.simd, rhs.simd);
 
         Self { simd: u32x4_shuffle::<1, 3, 5, 7>(low, high) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let l = vmull_u32(vget_low_u32(self.neon), vget_low_u32(rhs.neon));
           let h = vmull_u32(vget_high_u32(self.neon), vget_high_u32(rhs.neon));
@@ -1149,7 +1149,7 @@
         Self { sse: unpack_low_i32_m128i(self.sse, b.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_shuffle::<0, 4, 1, 5>(self.simd, b.simd) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vzip1q_u32(self.neon, b.neon) } }
       } else {
         let s = self.as_array();
@@ -1169,7 +1169,7 @@
         Self { sse: unpack_high_i32_m128i(self.sse, b.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u32x4_shuffle::<2, 6, 3, 7>(self.simd, b.simd) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vzip2q_u32(self.neon, b.neon) } }
       } else {
         let s = self.as_array();
