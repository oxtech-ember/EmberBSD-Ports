$NetBSD: patch-.._vendor_wide-0.7.33_src_u8x16__.rs,v 1.1 2025/12/08 12:40:17 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/u8x16_.rs.orig
+++ ../vendor/wide-1.7.1/src/u8x16_.rs
@@ -37,7 +37,7 @@
     }
 
     impl Eq for u8x16 { }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
     use core::arch::aarch64::*;
 
     /// A SIMD vector with 16 elements of type [`u8`].
@@ -104,7 +104,7 @@
         Self { sse: add_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_add(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vaddq_u8(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -136,7 +136,7 @@
         Self { sse: sub_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_sub(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vsubq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -167,7 +167,7 @@
     // to `i16` then converting back after multiplication, but that may not
     // actually be faster than auto-vectorization.
     pick! {
-      if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vmulq_u8(self.neon, rhs.neon) } }
       } else {
         let self_array: [u8; 16] = cast(self);
@@ -202,7 +202,7 @@
         Self { sse: bitand_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_and(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vandq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -234,7 +234,7 @@
         Self { sse: bitor_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_or(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vorrq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -266,7 +266,7 @@
         Self { sse: bitxor_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_xor(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: veorq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -298,7 +298,7 @@
         Self { sse: cmp_eq_mask_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_eq(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vceqq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -330,7 +330,7 @@
         !self.simd_eq(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_ne(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_eq(rhs)
       } else {
         Self { arr: [
@@ -366,7 +366,7 @@
         Self { sse: cmp_lt_mask_i8_m128i(self_i8, rhs_i8) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_lt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vcltq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -402,7 +402,7 @@
         Self { sse: cmp_gt_mask_i8_m128i(self_i8, rhs_i8) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vcgtq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -440,7 +440,7 @@
         Self { sse: gt_mask.bitxor(u8x16::splat(0xFF)).sse }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vcleq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -478,7 +478,7 @@
         Self { sse: lt_mask.bitxor(u8x16::splat(0xFF)).sse }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vcgeq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -539,7 +539,7 @@
         let rhs = u8x16_shuffle::<1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0>(sum, sum);
         let sum = u8x16_add(sum, rhs);
         u8x16_extract_lane::<0>(sum)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Use `transmute` instead of `cast` because `uint8x16_t` does not
           // implement `bytemuck::Pod`.
@@ -563,7 +563,7 @@
   #[inline]
   pub fn reduce_mul(self) -> u8 {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         const HIGH_64: [u8; 16] = [8, 9, 10, 11, 12, 13, 14, 15, 0, 0, 0, 0, 0, 0, 0, 0];
         const HIGH_32: [u8; 16] = [4, 5, 6, 7, 0, 1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0];
         const HIGH_16: [u8; 16] = [2, 3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
@@ -600,7 +600,7 @@
         }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_one.simd, if_zero.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_u8(self.neon, if_one.neon, if_zero.neon) }}
       } else {
         generic_bit_blend(self, if_one, if_zero)
@@ -615,7 +615,7 @@
         Self { sse: blend_varying_i8_m128i(if_false.sse, if_true.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_true.simd, if_false.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_u8(self.neon, if_true.neon, if_false.neon) }}
       } else {
         generic_bit_blend(self, if_true, if_false)
@@ -630,7 +630,7 @@
         move_mask_i8_m128i(self.sse) as u32
       } else if #[cfg(target_feature="simd128")] {
         u8x16_bitmask(self.simd) as u32
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // set all to 1 if top bit is set, else 0
           let masked = vcltzq_s8(self.cast_signed().neon);
@@ -674,7 +674,7 @@
         move_mask_i8_m128i(self.sse) != 0
       } else if #[cfg(target_feature="simd128")] {
         u8x16_bitmask(self.simd) != 0
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           vminvq_s8(self.cast_signed().neon) < 0
         }
@@ -692,7 +692,7 @@
         move_mask_i8_m128i(self.sse) == 0b1111_1111_1111_1111
       } else if #[cfg(target_feature="simd128")] {
         u8x16_bitmask(self.simd) == 0b1111_1111_1111_1111
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           vmaxvq_s8(self.cast_signed().neon) < 0
         }
@@ -712,7 +712,7 @@
         Self { simd: u8x16_relaxed_swizzle(self.simd, indices.simd) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_swizzle(self.simd, indices.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vqtbl1q_u8(self.neon, indices.neon) } }
       } else {
         let self_array = self.to_array();
@@ -782,7 +782,7 @@
             m128i(_mm_permutex2var_epi8(self[0].sse.0, indices.sse.0, self[1].sse.0))
           },
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         let table = uint8x16x2_t(self[0].neon, self[1].neon);
         unsafe { u8x16 { neon: vqtbl2q_u8(table, indices.neon) } }
       } else {
@@ -817,7 +817,7 @@
   #[inline]
   fn shuffle(self: [u8x16; 3], indices: u8x16) -> u8x16 {
     pick! {
-      if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         let table = uint8x16x3_t(self[0].neon, self[1].neon, self[2].neon);
         unsafe { u8x16 { neon: vqtbl3q_u8(table, indices.neon) } }
       } else {
@@ -839,7 +839,7 @@
   #[inline]
   fn shuffle(self: [u8x16; 4], indices: u8x16) -> u8x16 {
     pick! {
-      if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         let table = uint8x16x4_t(self[0].neon, self[1].neon, self[2].neon, self[3].neon);
         unsafe { u8x16 { neon: vqtbl4q_u8(table, indices.neon) } }
       } else {
@@ -913,7 +913,7 @@
     // to `u16` or `u32` then converting back after multiplication, but that may
     // not actually be faster than auto-vectorization.
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Mask `rhs` to 7 to match `wrapping_shl`.
           let shift_by = vreinterpretq_s8_u8(vandq_u8(rhs.neon, vmovq_n_u8(7)));
@@ -954,7 +954,7 @@
       if #[cfg(target_feature="simd128")] {
         // Mask `rhs` to 7 to match `wrapping_shl`.
         Self { simd: u8x16_shl(self.simd, rhs & 7) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Mask `rhs` to 7 to match `wrapping_shl`.
         unsafe { Self { neon: vshlq_u8(self.neon, vmovq_n_s8(rhs as i8 & 7)) } }
       } else {
@@ -973,7 +973,7 @@
     // to `u16` or `u32` then converting back after multiplication, but that may
     // not actually be faster than auto-vectorization.
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Mask `rhs` to 7 to match `wrapping_shr`, and negate it because
           // there is no shift-right intrinsic.
@@ -1015,7 +1015,7 @@
       if #[cfg(target_feature="simd128")] {
         // Mask `rhs` to 7 to match `wrapping_shr`.
         Self { simd: u8x16_shr(self.simd, rhs & 7) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Mask `rhs` to 7 to match `wrapping_shr`, and negate it because
         // there is no shift-right intrinsic.
         unsafe { Self { neon: vshlq_u8(self.neon, vmovq_n_s8(-(rhs as i8 & 7))) } }
@@ -1036,7 +1036,7 @@
         Self { sse: max_u8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_max(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -1068,7 +1068,7 @@
         Self { sse: min_u8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_min(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -1129,7 +1129,7 @@
         let rhs = u8x16_shuffle::<1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0>(max, max);
         let max = u8x16_max(max, rhs);
         u8x16_extract_lane::<0>(max)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Use `transmute` instead of `cast` because `uint8x16_t` does not
           // implement `bytemuck::Pod`.
@@ -1186,7 +1186,7 @@
         let rhs = u8x16_shuffle::<1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0>(min, min);
         let min = u8x16_min(min, rhs);
         u8x16_extract_lane::<0>(min)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Use `transmute` instead of `cast` because `uint8x16_t` does not
           // implement `bytemuck::Pod`.
@@ -1213,7 +1213,7 @@
     // or `u32` then converting back after multiplication, but that may not
     // actually be faster than auto-vectorization.
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           Self { neon: vshlq_u8(self.neon, vreinterpretq_s8_u8(rhs.neon)) } & rhs.simd_lt(8)
         }
@@ -1252,7 +1252,7 @@
       if #[cfg(target_feature="simd128")] {
         // The intrinsic performs wrapping shift so we need to mask the result.
         if rhs >= 8 { Self::ZERO } else { Self { simd: u8x16_shl(self.simd, rhs) } }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // The intrinsic has different semantics so we need to saturate `rhs`.
         unsafe { Self { neon: vshlq_u8(self.neon, vmovq_n_s8(rhs.min(i8::MAX as u32) as i8)) } }
       } else {
@@ -1270,7 +1270,7 @@
     // to `u16` or `u32` then converting back after multiplication, but that may
     // not actually be faster than auto-vectorization.
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // mask to hide `rhs` overflow.
@@ -1310,7 +1310,7 @@
     pick! {
       if #[cfg(target_feature="simd128")] {
         if rhs < 8 { Self { simd: u8x16_shr(self.simd, rhs) } } else { Self::ZERO }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -1332,7 +1332,7 @@
         Self { sse: add_saturating_u8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_add_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vqaddq_u8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -1364,7 +1364,7 @@
         Self { sse: sub_saturating_u8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u8x16_sub_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqsubq_u8(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -1400,7 +1400,7 @@
     #[inline]
     pub fn widening_mul(self, rhs: Self) -> u16x16 {
       pick! {
-        if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+        if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
           unsafe {
             let low_wide_mul = vmull_u8(vget_low_u8(self.neon), vget_low_u8(rhs.neon));
             let high_wide_mul = vmull_u8(vget_high_u8(self.neon), vget_high_u8(rhs.neon));
@@ -1440,7 +1440,7 @@
   #[inline]
   pub fn mul_keep_low_high(self, rhs: Self) -> (Self, Self) {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_u8_u16(
             vmull_u8(vget_low_u8(self.neon), vget_low_u8(rhs.neon)),
@@ -1525,7 +1525,7 @@
   #[inline]
   pub fn mul_keep_high(self, rhs: Self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_u8_u16(
             vmull_u8(vget_low_u8(self.neon), vget_low_u8(rhs.neon)),
@@ -1577,7 +1577,7 @@
             u8x16 { sse: unpack_low_i8_m128i(lhs.sse, rhs.sse) }
         } else if #[cfg(target_feature = "simd128")] {
           u8x16 { simd: u8x16_shuffle::<0, 16, 1, 17, 2, 18, 3, 19, 4, 20, 5, 21, 6, 22, 7, 23>(lhs.simd, rhs.simd) }
-        } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64"))] {
+        } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64",target_endian="little"))] {
             let lhs = unsafe { vget_low_u8(lhs.neon) };
             let rhs = unsafe { vget_low_u8(rhs.neon) };
 
@@ -1608,7 +1608,7 @@
             u8x16 { sse: unpack_high_i8_m128i(lhs.sse, rhs.sse) }
         } else if #[cfg(target_feature = "simd128")] {
             u8x16 { simd: u8x16_shuffle::<8, 24, 9, 25, 10, 26, 11, 27, 12, 28, 13, 29, 14, 30, 15, 31>(lhs.simd, rhs.simd) }
-        } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64"))] {
+        } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64",target_endian="little"))] {
             let lhs = unsafe { vget_high_u8(lhs.neon) };
             let rhs = unsafe { vget_high_u8(rhs.neon) };
 
@@ -1639,7 +1639,7 @@
             u8x16 { sse: pack_i16_to_u8_m128i(lhs.sse, rhs.sse) }
         } else if #[cfg(target_feature = "simd128")] {
             u8x16 { simd: u8x16_narrow_i16x8(lhs.simd, rhs.simd) }
-        } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64"))] {
+        } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64",target_endian="little"))] {
             let lhs = unsafe { vqmovun_s16(lhs.neon) };
             let rhs = unsafe { vqmovun_s16(rhs.neon) };
             u8x16 { neon: unsafe { vcombine_u8(lhs, rhs) } }
