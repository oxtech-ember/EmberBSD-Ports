$NetBSD: patch-.._vendor_wide-0.7.33_src_f32x4__.rs,v 1.1 2025/12/08 12:40:16 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/f32x4_.rs.orig
+++ ../vendor/wide-1.7.1/src/f32x4_.rs
@@ -35,7 +35,7 @@
         u32x4_all_true(f32x4_eq(self.simd, other.simd))
       }
     }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
     use core::arch::aarch64::*;
 
     /// A SIMD vector with four elements of type [`f32`].
@@ -103,7 +103,7 @@
         Self { sse: bitxor_m128(self.sse, Self::splat(-0.0).sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_neg(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vnegq_f32(self.neon) }}
       } else {
         Self { arr: [
@@ -128,7 +128,7 @@
         Self { sse: add_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_add(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vaddq_f32(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -148,7 +148,7 @@
         Self { sse: sub_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_sub(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vsubq_f32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -168,7 +168,7 @@
         Self { sse: mul_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_mul(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmulq_f32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -188,7 +188,7 @@
         Self { sse: div_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_div(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vdivq_f32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -218,7 +218,7 @@
         Self { sse: bitand_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_and(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vandq_u32(vreinterpretq_u32_f32(self.neon), vreinterpretq_u32_f32(rhs.neon))) }}
       } else {
         Self { arr: [
@@ -238,7 +238,7 @@
         Self { sse: bitor_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_or(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vorrq_u32(vreinterpretq_u32_f32(self.neon), vreinterpretq_u32_f32(rhs.neon))) }}
       } else {
         Self { arr: [
@@ -258,7 +258,7 @@
         Self { sse: bitxor_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_xor(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(veorq_u32(vreinterpretq_u32_f32(self.neon), vreinterpretq_u32_f32(rhs.neon))) }}
       } else {
         Self { arr: [
@@ -278,7 +278,7 @@
         Self { sse: cmp_eq_mask_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_eq(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vceqq_f32(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -298,7 +298,7 @@
         Self { sse: cmp_neq_mask_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_ne(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vmvnq_u32(vceqq_f32(self.neon, rhs.neon))) }}
       } else {
         Self { arr: [
@@ -318,7 +318,7 @@
         Self { sse: cmp_lt_mask_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_lt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vcltq_f32(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -338,7 +338,7 @@
         Self { sse: cmp_gt_mask_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vcgtq_f32(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -358,7 +358,7 @@
         Self { sse: cmp_le_mask_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vcleq_f32(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -378,7 +378,7 @@
         Self { sse: cmp_ge_mask_m128(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vcgeq_f32(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -415,7 +415,7 @@
         }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_one.simd, if_zero.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_f32(vreinterpretq_u32_f32(self.neon), if_one.neon, if_zero.neon) }}
       } else {
         generic_bit_blend(self, if_one, if_zero)
@@ -430,7 +430,7 @@
         Self { sse: blend_varying_m128(if_false.sse, if_true.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_true.simd, if_false.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_f32(vreinterpretq_u32_f32(self.neon), if_true.neon, if_false.neon) }}
       } else {
         generic_bit_blend(self, if_true, if_false)
@@ -445,7 +445,7 @@
         move_mask_m128(self.sse) as u32
       } else if #[cfg(target_feature="simd128")] {
         u32x4_bitmask(self.simd) as u32
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe
         {
           // set all to 1 if top bit is set, else 0
@@ -504,7 +504,7 @@
         transpose_four_m128(&mut e0.sse, &mut e1.sse, &mut e2.sse, &mut e3.sse);
 
         [e0, e1, e2, e3]
-      } else if #[cfg(any(all(target_feature="neon",target_arch="aarch64"), target_feature="simd128"))] {
+      } else if #[cfg(any(all(target_feature="neon",target_arch="aarch64",target_endian="little"), target_feature="simd128"))] {
         let a = data[0].unpack_lo(data[2]);
         let b = data[1].unpack_lo(data[3]);
         let c = data[0].unpack_hi(data[2]);
@@ -544,7 +544,7 @@
         Self { sse: cmp_unord_mask_m128(self.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_ne(self.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f32_u32(vmvnq_u32(vceqq_f32(self.neon, self.neon))) }}
       } else {
         Self { arr: [
@@ -602,7 +602,7 @@
         Self { sse: reciprocal_m128(self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_div(f32x4_splat(1.0), self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vdivq_f32(vdupq_n_f32(1.0), self.neon) }}
       } else {
         Self { arr: [
@@ -622,7 +622,7 @@
         Self { sse: reciprocal_sqrt_m128(self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_div(f32x4_splat(1.0), f32x4_sqrt(self.simd)) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vdivq_f32(vdupq_n_f32(1.0), vsqrtq_f32(self.neon)) }}
       } else if #[cfg(feature="std")] {
         Self { arr: [
@@ -664,7 +664,7 @@
             f32x4_ne(self.simd, self.simd), // NaN check
           )
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxnmq_f32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -686,7 +686,7 @@
         Self {
           simd: f32x4_pmax(self.simd, rhs.simd),
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_f32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -721,7 +721,7 @@
             f32x4_ne(self.simd, self.simd), // NaN check
           )
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminnmq_f32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -743,7 +743,7 @@
         Self {
           simd: f32x4_pmin(self.simd, rhs.simd),
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminq_f32(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -761,7 +761,7 @@
     pick! {
       if #[cfg(any(
         target_feature="simd128",
-        all(target_feature="neon",target_arch="aarch64"),
+        all(target_feature="neon",target_arch="aarch64",target_endian="little"),
       ))] {
         // `fast_clamp` already works.
         self.fast_clamp(min, max)
@@ -781,7 +781,7 @@
         Self { sse: max_m128(min.sse, min_m128(max.sse, self.sse)) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_max(f32x4_min(self.simd, max.simd), min.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vmaxq_f32(vminq_f32(self.neon, max.neon), min.neon) } }
       } else {
         // The standard library does not have NaN propagating `min` and `max`
@@ -799,7 +799,7 @@
     pick! {
       if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_abs(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vabsq_f32(self.neon) }}
       } else {
         let non_sign_bits = f32x4::from(f32::from_bits(i32::MAX as u32));
@@ -815,7 +815,7 @@
         Self { simd: f32x4_floor(self.simd) }
       } else if #[cfg(target_feature="sse4.1")] {
         Self { sse: floor_m128(self.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vrndmq_f32(self.neon) }}
       } else if #[cfg(feature="std")] {
         let base: [f32; 4] = cast(self);
@@ -840,7 +840,7 @@
         Self { simd: f32x4_ceil(self.simd) }
       } else if #[cfg(target_feature="sse4.1")] {
         Self { sse: ceil_m128(self.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vrndpq_f32(self.neon) }}
       } else if #[cfg(feature="std")] {
         let base: [f32; 4] = cast(self);
@@ -914,7 +914,7 @@
 
         // `abs` keeps the original sign.
         bounds_mask.abs().bitselect(result_abs, self)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vrndaq_f32(self.neon) }}
       } else {
         const_f32_as_f32x4!(HALF_NEXT_DOWN, 0.5_f32.next_down());
@@ -954,7 +954,7 @@
         flip_to_max ^ cast
       } else if #[cfg(target_feature="simd128")] {
         cast(Self { simd: i32x4_trunc_sat_f32x4(f32x4_nearest(self.simd)) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         cast(unsafe {Self { neon: vreinterpretq_f32_s32(vcvtnq_s32_f32(self.neon)) }})
       } else {
         let rounded: [f32; 4] = cast(self.round());
@@ -992,7 +992,7 @@
         mask.select(self, f)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_nearest(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vrndnq_f32(self.neon) }}
       } else {
         // Note(Lokathor): This software fallback is probably very slow compared
@@ -1045,7 +1045,7 @@
         bounds_mask.abs().select(result, self)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_trunc(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vrndq_f32(self.neon) } }
       } else {
         let array: [f32; 4] = cast(self);
@@ -1078,7 +1078,7 @@
         flip_to_max ^ cast
       } else if #[cfg(target_feature="simd128")] {
         cast(Self { simd: i32x4_trunc_sat_f32x4(self.simd) })
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         cast(unsafe {Self { neon: vreinterpretq_f32_s32(vcvtq_s32_f32(self.neon)) }})
       } else {
         let n: [f32;4] = cast(self);
@@ -1115,7 +1115,7 @@
     pick! {
       if #[cfg(all(target_feature="sse2",target_feature="fma"))] {
         Self { sse: fused_mul_add_m128(self.sse, a.sse, b.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vfmaq_f32(b.neon, self.neon, a.neon) } }
       } else {
         (self * a) + b
@@ -1136,7 +1136,7 @@
     pick! {
       if #[cfg(all(target_feature="sse2",target_feature="fma"))] {
         Self { sse: fused_mul_sub_m128(self.sse, a.sse, b.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vfmaq_f32(vnegq_f32(b.neon), self.neon, a.neon) } }
       } else {
         (self * a) - b
@@ -1156,7 +1156,7 @@
     pick! {
       if #[cfg(all(target_feature="sse2",target_feature="fma"))] {
         Self { sse: fused_mul_neg_add_m128(self.sse, a.sse, b.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vfmsq_f32(b.neon, self.neon, a.neon) } }
       } else {
         b - (self * a)
@@ -1177,7 +1177,7 @@
     pick! {
       if #[cfg(all(target_feature="sse2",target_feature="fma"))] {
         Self { sse: fused_mul_neg_sub_m128(self.sse, a.sse, b.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vnegq_f32(vfmaq_f32(b.neon, self.neon, a.neon)) } }
       } else {
         -(self * a) - b
@@ -1304,7 +1304,7 @@
         Self { sse: sqrt_m128(self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_sqrt(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vsqrtq_f32(self.neon) }}
       } else if #[cfg(feature="std")] {
         Self { arr: [
@@ -2005,7 +2005,7 @@
         Self {
           simd: u32x4_shuffle::<0, 4, 1, 5>(self.simd, b.simd)
         }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vzip1q_f32(self.neon, b.neon) }}
       } else {
         Self { arr: [
@@ -2029,7 +2029,7 @@
         Self {
           simd: u32x4_shuffle::<2, 6, 3, 7>(self.simd, b.simd)
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vzip2q_f32(self.neon, b.neon) }}
       } else {
         Self { arr: [
@@ -2050,7 +2050,7 @@
         Self { sse: convert_to_m128_from_i32_m128i(v.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f32x4_convert_i32x4(v.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vcvtq_f32_s32(v.neon) }}
       } else {
         Self { arr: [
