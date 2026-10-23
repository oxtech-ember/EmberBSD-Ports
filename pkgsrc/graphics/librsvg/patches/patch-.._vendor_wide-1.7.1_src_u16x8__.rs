$NetBSD: patch-.._vendor_wide-0.7.33_src_u16x8__.rs,v 1.1 2025/12/08 12:40:17 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/u16x8_.rs.orig
+++ ../vendor/wide-1.7.1/src/u16x8_.rs
@@ -37,7 +37,7 @@
     }
 
     impl Eq for u16x8 { }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
       use core::arch::aarch64::*;
 
       /// A SIMD vector with eight elements of type [`u16`].
@@ -104,7 +104,7 @@
         Self { sse: add_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_add(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vaddq_u16(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -128,7 +128,7 @@
         Self { sse: sub_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_sub(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vsubq_u16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -152,7 +152,7 @@
         Self { sse: mul_i16_keep_low_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_mul(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmulq_u16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -176,7 +176,7 @@
         Self { sse: bitand_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_and(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vandq_u16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -200,7 +200,7 @@
         Self { sse: bitor_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_or(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vorrq_u16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -224,7 +224,7 @@
         Self { sse: bitxor_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_xor(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: veorq_u16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -248,7 +248,7 @@
         Self { sse: cmp_eq_mask_i16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_eq(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vceqq_u16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -272,7 +272,7 @@
         !self.simd_eq(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_ne(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_eq(rhs)
       } else {
         Self { arr: [
@@ -310,7 +310,7 @@
         Self { sse: mask }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64"))] {
+      } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64",target_endian="little"))] {
         unsafe {
           use core::arch::aarch64::*;
           Self {
@@ -341,7 +341,7 @@
         !self.simd_gt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_gt(rhs)
       } else {
         Self { arr: [
@@ -365,7 +365,7 @@
         !self.simd_lt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_lt(rhs)
       } else {
         Self { arr: [
@@ -394,7 +394,7 @@
         let lo16 = shr_imm_u32_m128i::<16>(sum32);
         let sum16 = add_i16_m128i(sum32, lo16);
         extract_i16_as_i32_m128i::<0>(sum16) as u16
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vaddvq_u16(self.neon) }
       } else {
         let arr: [u16; 8] = cast(self);
@@ -431,7 +431,7 @@
         let high_16 = u16x8_shuffle::<1, 0, 0, 0, 0, 0, 0, 0>(reduce_32, reduce_32);
         let reduce_16 = u16x8_mul(reduce_32, high_16);
         u16x8_extract_lane::<0>(reduce_16)
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let high_64 = vextq_u16::<4>(self.neon, self.neon);
           let reduce_64 = vmulq_u16(self.neon, high_64);
@@ -469,7 +469,7 @@
         }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_one.simd, if_zero.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_u16(self.neon, if_one.neon, if_zero.neon) }}
       } else {
         generic_bit_blend(self, if_one, if_zero)
@@ -484,7 +484,7 @@
         Self { sse: blend_varying_i8_m128i(if_false.sse, if_true.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_true.simd, if_false.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_u16(self.neon, if_true.neon, if_false.neon) }}
       } else {
         generic_bit_blend(self, if_true, if_false)
@@ -499,7 +499,7 @@
         (move_mask_i8_m128i( pack_i16_to_i8_m128i(self.sse,self.sse)) as u32) & 0xff
       } else if #[cfg(target_feature="simd128")] {
         u16x8_bitmask(self.simd) as u32
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe
         {
           // set all to 1 if top bit is set, else 0
@@ -532,7 +532,7 @@
         (move_mask_i8_m128i(self.sse) & 0b1010101010101010) != 0
       } else if #[cfg(target_feature="simd128")] {
         u16x8_bitmask(self.simd) != 0
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           vminvq_s16(self.cast_signed().neon) < 0
         }
@@ -550,7 +550,7 @@
         (move_mask_i8_m128i(self.sse) & 0b1010101010101010) == 0b1010101010101010
       } else if #[cfg(target_feature="simd128")] {
         u16x8_bitmask(self.simd) == 0b11111111
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           vmaxvq_s16(self.cast_signed().neon) < 0
         }
@@ -743,7 +743,7 @@
           Self { sse: unpack_low_i64_m128i(b4, b8) },
           Self { sse: unpack_high_i64_m128i(b4, b8) } ,
         ]
-     } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+     } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
 
           #[inline] fn vtrq32(a : uint16x8_t, b : uint16x8_t) -> (uint16x8_t, uint16x8_t)
           {
@@ -857,7 +857,7 @@
         let rhs = bitand_m128i(rhs.sse, set_splat_i16_m128i(15));
         // TODO(safe_arch): Add `_mm_sllv_epi16`.
         cast(unsafe { _mm_sllv_epi16(self.sse.0, rhs.0) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Mask `rhs` to 15 to match `wrapping_shl`.
           let rhs = vreinterpretq_s16_u16(vandq_u16(rhs.neon, vmovq_n_u16(15)));
@@ -891,7 +891,7 @@
         Self { sse: shl_all_u16_m128i(self.sse, shift) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_shl(self.simd, rhs) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Use `rhs % 16` to perform wrapping shift and not unbounded shift.
         #[expect(clippy::suspicious_arithmetic_impl)]
         unsafe {Self { neon: vshlq_u16(self.neon, vmovq_n_s16(rhs as i16 & 15)) }}
@@ -923,7 +923,7 @@
         let rhs = bitand_m128i(rhs.sse, set_splat_i16_m128i(15));
         // TODO(safe_arch): Add `_mm_srlv_epi16`.
         cast(unsafe { _mm_srlv_epi16(self.sse.0, rhs.0) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Mask `rhs` to 15 to match `wrapping_shr`, and negate it because
           // there is no shift-right intrinsic.
@@ -958,7 +958,7 @@
         Self { sse: shr_all_u16_m128i(self.sse, shift) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_shr(self.simd, rhs) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Use `rhs % 16` to perform wrapping shift and not unbounded shift.
         #[expect(clippy::suspicious_arithmetic_impl)]
         unsafe {Self { neon: vshlq_u16(self.neon, vmovq_n_s16( -(rhs as i16 & 15))) }}
@@ -984,7 +984,7 @@
         Self { sse: max_u16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_max(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_u16(self.neon, rhs.neon) }}
       } else {
         let arr: [u16; 8] = cast(self);
@@ -1010,7 +1010,7 @@
         Self { sse: min_u16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_min(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminq_u16(self.neon, rhs.neon) }}
       } else {
         let arr: [u16; 8] = cast(self);
@@ -1040,7 +1040,7 @@
         let lo16 = shr_imm_u32_m128i::<16>(sum32);
         let sum16 = max_u16_m128i(sum32, lo16);
         extract_i16_as_i32_m128i::<0>(sum16) as u16
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vmaxvq_u16(self.neon) }
       } else {
         let arr: [u16; 8] = cast(self);
@@ -1069,7 +1069,7 @@
         let lo16 = shr_imm_u32_m128i::<16>(sum32);
         let sum16 = min_u16_m128i(sum32, lo16);
         extract_i16_as_i32_m128i::<0>(sum16) as u16
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vminvq_u16(self.neon) }
       } else {
         let arr: [u16; 8] = cast(self);
@@ -1098,7 +1098,7 @@
 
         // TODO(safe_arch): Add `_mm_sllv_epi16`.
         cast(unsafe { _mm_sllv_epi16(self.sse.0, rhs.sse.0) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // The intrinsic has different semantics so we need to mask ourselves.
           Self { neon: vshlq_u16(self.neon, vreinterpretq_s16_u16(rhs.neon)) } & rhs.simd_lt(16)
@@ -1129,7 +1129,7 @@
       } else if #[cfg(target_feature="simd128")] {
         // The intrinsic performs wrapping shift so we need to mask the result.
         if rhs >= 16 { Self::ZERO } else { Self { simd: u16x8_shl(self.simd, rhs) } }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // The intrinsic has different semantics so we need to saturate `rhs`.
         unsafe { Self { neon: vshlq_u16(self.neon, vmovq_n_s16(rhs.min(16) as i16)) } }
       } else {
@@ -1158,7 +1158,7 @@
 
         // TODO(safe_arch): Add `_mm_srlv_epi16`.
         cast(unsafe { _mm_srlv_epi16(self.sse.0, rhs.sse.0) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // mask to hide `rhs` overflow.
@@ -1189,7 +1189,7 @@
         Self { sse: shr_all_u16_m128i(self.sse, cast([rhs as u64, 0])) }
       } else if #[cfg(target_feature="simd128")] {
         if rhs < 16 { Self { simd: u16x8_shr(self.simd, rhs) } } else { Self::ZERO }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -1219,7 +1219,7 @@
         Self { sse: add_saturating_u16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_add_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vqaddq_u16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -1243,7 +1243,7 @@
         Self { sse: sub_saturating_u16_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u16x8_sub_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vqsubq_u16(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -1282,7 +1282,7 @@
             a: u32x4 { sse:unpack_low_i16_m128i(low, high) },
             b: u32x4 { sse:unpack_high_i16_m128i(low, high) }
           }
-        } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+        } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
           let lhs_low = unsafe { vget_low_u16(self.neon) };
           let rhs_low = unsafe { vget_low_u16(rhs.neon) };
 
@@ -1321,7 +1321,7 @@
           Self { simd: u16x8_shuffle::<0, 2, 4, 6, 8, 10, 12, 14>(low_wide_mul, high_wide_mul) },
           Self { simd: u16x8_shuffle::<1, 3, 5, 7, 9, 11, 13, 15>(low_wide_mul, high_wide_mul) },
         )
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_u16_u32(
             vmull_u16(vget_low_u16(self.neon), vget_low_u16(rhs.neon)),
@@ -1384,7 +1384,7 @@
     pick! {
       if #[cfg(target_feature="sse2")] {
         Self { sse: mul_u16_keep_high_m128i(self.sse, rhs.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         let lhs_low = unsafe { vget_low_u16(self.neon) };
         let rhs_low = unsafe { vget_low_u16(rhs.neon) };
 
