$NetBSD: patch-.._vendor_wide-0.7.33_src_f64x2__.rs,v 1.1 2025/12/08 12:40:16 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/f64x2_.rs.orig
+++ ../vendor/wide-1.7.1/src/f64x2_.rs
@@ -35,7 +35,7 @@
         u64x2_all_true(f64x2_eq(self.simd, other.simd))
       }
     }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
     use core::arch::aarch64::*;
 
     /// A SIMD vector with two elements of type [`f64`].
@@ -106,7 +106,7 @@
         Self { sse: bitxor_m128d(self.sse, Self::splat(-0.0).sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_neg(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vnegq_f64(self.neon) }}
       } else {
         Self { arr: [
@@ -124,7 +124,7 @@
         Self { sse: self.sse.not() }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_not(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u32(vmvnq_u32(vreinterpretq_u32_f64(self.neon))) }}
       } else {
         Self { arr: [
@@ -142,7 +142,7 @@
         Self { sse: add_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_add(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vaddq_f64(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -160,7 +160,7 @@
         Self { sse: sub_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_sub(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vsubq_f64(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -178,7 +178,7 @@
         Self { sse: mul_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_mul(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmulq_f64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -196,7 +196,7 @@
         Self { sse: div_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_div(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vdivq_f64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -222,7 +222,7 @@
         Self { sse: bitand_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_and(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vandq_u64(vreinterpretq_u64_f64(self.neon), vreinterpretq_u64_f64(rhs.neon))) }}
       } else {
         Self { arr: [
@@ -240,7 +240,7 @@
         Self { sse: bitor_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_or(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vorrq_u64(vreinterpretq_u64_f64(self.neon), vreinterpretq_u64_f64(rhs.neon))) }}
       } else {
         Self { arr: [
@@ -258,7 +258,7 @@
         Self { sse: bitxor_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_xor(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(veorq_u64(vreinterpretq_u64_f64(self.neon), vreinterpretq_u64_f64(rhs.neon))) }}
       } else {
         Self { arr: [
@@ -276,7 +276,7 @@
         Self { sse: cmp_eq_mask_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_eq(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vceqq_f64(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -294,7 +294,7 @@
         Self { sse: cmp_neq_mask_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_ne(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vceqq_f64(self.neon, rhs.neon)) }.not() }
       } else {
         Self { arr: [
@@ -312,7 +312,7 @@
         Self { sse: cmp_lt_mask_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_lt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vcltq_f64(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -332,7 +332,7 @@
         Self { sse: cmp_gt_mask_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vcgtq_f64(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -350,7 +350,7 @@
         Self { sse: cmp_le_mask_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vcleq_f64(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -368,7 +368,7 @@
         Self { sse: cmp_ge_mask_m128d(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vcgeq_f64(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -388,7 +388,7 @@
       } else if #[cfg(any(target_feature="sse2", target_feature="simd128"))] {
         let a: [f64;2] = cast(self);
         a.iter().sum()
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vgetq_lane_f64(self.neon,0) + vgetq_lane_f64(self.neon,1) }
       } else {
         self.arr.iter().sum()
@@ -414,7 +414,7 @@
         }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_one.simd, if_zero.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_f64(vreinterpretq_u64_f64(self.neon), if_one.neon, if_zero.neon) }}
       } else {
         generic_bit_blend(self, if_one, if_zero)
@@ -429,7 +429,7 @@
         Self { sse: blend_varying_m128d(if_false.sse, if_true.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_true.simd, if_false.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_f64(vreinterpretq_u64_f64(self.neon), if_true.neon, if_false.neon) }}
       } else {
         generic_bit_blend(self, if_true, if_false)
@@ -444,7 +444,7 @@
         move_mask_m128d(self.sse) as u32
       } else if #[cfg(target_feature="simd128")] {
         u64x2_bitmask(self.simd) as u32
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe
         {
           let e = vreinterpretq_u64_f64(self.neon);
@@ -488,7 +488,7 @@
     pick! {
       if #[cfg(any(
         target_feature="sse2",
-        all(target_feature="neon",target_arch="aarch64"),
+        all(target_feature="neon",target_arch="aarch64",target_endian="little"),
         target_feature="simd128",
       ))] {
         [data[0].unpack_lo(data[1]), data[0].unpack_hi(data[1])]
@@ -506,7 +506,7 @@
         Self { sse: cmp_unord_mask_m128d(self.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_ne(self.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_f64_u64(vceqq_f64(self.neon, self.neon)) }.not() }
       } else {
         Self { arr: [
@@ -611,7 +611,7 @@
             f64x2_ne(self.simd, self.simd), // NaN check
           )
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxnmq_f64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -631,7 +631,7 @@
         Self {
           simd: f64x2_pmax(self.simd, rhs.simd),
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_f64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -664,7 +664,7 @@
             f64x2_ne(self.simd, self.simd), // NaN check
           )
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminnmq_f64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -684,7 +684,7 @@
         Self {
           simd: f64x2_pmin(self.simd, rhs.simd),
         }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminq_f64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -700,7 +700,7 @@
     pick! {
       if #[cfg(any(
         target_feature="simd128",
-        all(target_feature="neon",target_arch="aarch64"),
+        all(target_feature="neon",target_arch="aarch64",target_endian="little"),
       ))] {
         // `fast_clamp` already works.
         self.fast_clamp(min, max)
@@ -720,7 +720,7 @@
         Self { sse: max_m128d(min.sse, min_m128d(max.sse, self.sse)) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_max(f64x2_min(self.simd, max.simd), min.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vmaxq_f64(vminq_f64(self.neon, max.neon), min.neon) } }
       } else {
         // The standard library does not have NaN propagating `min` and `max`
@@ -738,7 +738,7 @@
     pick! {
       if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_abs(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vabsq_f64(self.neon) }}
       } else {
         let non_sign_bits = f64x2::from(f64::from_bits(i64::MAX as u64));
@@ -754,7 +754,7 @@
         Self { simd: f64x2_floor(self.simd) }
       } else if #[cfg(target_feature="sse4.1")] {
         Self { sse: floor_m128d(self.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vrndmq_f64(self.neon) }}
       } else if #[cfg(feature="std")] {
         let base: [f64; 2] = cast(self);
@@ -777,7 +777,7 @@
         Self { simd: f64x2_ceil(self.simd) }
       } else if #[cfg(target_feature="sse4.1")] {
         Self { sse: ceil_m128d(self.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vrndpq_f64(self.neon) }}
       } else if #[cfg(feature="std")] {
         let base: [f64; 2] = cast(self);
@@ -871,7 +871,7 @@
         // TODO(safe_arch): Add `_mm_cvtpd_epi64`.
         let cast: i64x2 = cast(m128i(unsafe { _mm_cvtpd_epi64(non_nan.sse.0) }));
         flip_to_max ^ cast
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         cast(Self { neon: unsafe { vreinterpretq_f64_s64(vcvtnq_s64_f64(self.neon)) } })
       } else {
         let rounded: [f64; 2] = cast(self.round_ties_even());
@@ -964,7 +964,7 @@
         // TODO(safe_arch): Add `_mm_cvttpd_epi64`.
         let cast: i64x2 = cast(m128i(unsafe { _mm_cvttpd_epi64(non_nan.sse.0) }));
         flip_to_max ^ cast
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         cast(Self { neon: unsafe { vreinterpretq_f64_s64(vcvtq_s64_f64(self.neon)) } })
       } else {
         // There does not seem to be an intrinsic for `wasm32`.
@@ -1003,7 +1003,7 @@
     pick! {
       if #[cfg(all(target_feature="fma"))] {
         Self { sse: fused_mul_add_m128d(self.sse, a.sse, b.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vfmaq_f64(b.neon, self.neon, a.neon) } }
       } else {
         (self * a) + b
@@ -1024,7 +1024,7 @@
     pick! {
       if #[cfg(all(target_feature="fma"))] {
         Self { sse: fused_mul_sub_m128d(self.sse, a.sse, b.sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         unsafe { Self { neon: vfmaq_f64(vnegq_f64(b.neon), self.neon, a.neon) } }
       } else {
         (self * a) - b
@@ -1044,7 +1044,7 @@
     pick! {
         if #[cfg(all(target_feature="fma"))] {
           Self { sse: fused_mul_neg_add_m128d(self.sse, a.sse, b.sse) }
-        } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+        } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
           unsafe { Self { neon: vfmsq_f64(b.neon, self.neon, a.neon) } }
         } else {
           b - (self * a)
@@ -1065,7 +1065,7 @@
     pick! {
         if #[cfg(all(target_feature="fma"))] {
           Self { sse: fused_mul_neg_sub_m128d(self.sse, a.sse, b.sse) }
-        } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+        } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
           unsafe { Self { neon: vnegq_f64(vfmaq_f64(b.neon, self.neon, a.neon)) } }
         } else {
           -(self * a) - b
@@ -1198,7 +1198,7 @@
         Self { sse: sqrt_m128d(self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_sqrt(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vsqrtq_f64(self.neon) }}
       } else if #[cfg(feature="std")] {
         Self { arr: [
@@ -2131,7 +2131,7 @@
         Self { sse: unpack_low_m128d(self.sse, b.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_shuffle::<0, 2>(self.simd, b.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vzip1q_f64(self.neon, b.neon) } }
       } else {
         Self::new([self.as_array()[0], b.as_array()[0]])
@@ -2149,7 +2149,7 @@
         Self { sse: unpack_high_m128d(self.sse, b.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_shuffle::<1, 3>(self.simd, b.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vzip2q_f64(self.neon, b.neon) } }
       } else {
         Self::new([self.as_array()[1], b.as_array()[1]])
@@ -2166,7 +2166,7 @@
         Self { sse: convert_to_m128d_from_lower2_i32_m128i(v.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: f64x2_convert_low_i32x4(v.simd)}
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vcvtq_f64_s64(vmovl_s32(vget_low_s32(v.neon))) }}
       } else {
         Self { arr: [
