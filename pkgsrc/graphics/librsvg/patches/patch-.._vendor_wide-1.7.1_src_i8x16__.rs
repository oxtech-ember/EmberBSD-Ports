$NetBSD: patch-.._vendor_wide-0.7.33_src_i8x16__.rs,v 1.1 2025/12/08 12:40:17 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/i8x16_.rs.orig
+++ ../vendor/wide-1.7.1/src/i8x16_.rs
@@ -37,7 +37,7 @@
     }
 
     impl Eq for i8x16 { }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
     use core::arch::aarch64::*;
 
     /// A SIMD vector with 16 elements of type [`i8`].
@@ -100,7 +100,7 @@
         Self { sse: cmp_lt_mask_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_lt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_s8_u8(vcltq_s8(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -132,7 +132,7 @@
         Self { sse: cmp_gt_mask_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_s8_u8(vcgtq_s8(self.neon, rhs.neon)) }}
       } else {
         Self { arr: [
@@ -164,7 +164,7 @@
         !self.simd_gt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_gt(rhs)
       } else {
         Self { arr: [
@@ -196,7 +196,7 @@
         !self.simd_lt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_lt(rhs)
       } else {
         Self { arr: [
@@ -227,7 +227,7 @@
     // to `i16` or `i32` then converting back after multiplication, but that may
     // not actually be faster than auto-vectorization.
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Mask `rhs` to 7 to match `wrapping_shr`, and negate it because
           // there is no shift-right intrinsic.
@@ -269,7 +269,7 @@
       if #[cfg(target_feature="simd128")] {
         // Mask `rhs` to 7 to match `wrapping_shr`.
         Self { simd: i8x16_shr(self.simd, rhs & 7) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Mask `rhs` to 7 to match `wrapping_shr`, and negate it because
         // there is no shift-right intrinsic.
         unsafe { Self { neon: vshlq_s8(self.neon, vmovq_n_s8(-(rhs as i8 & 7))) } }
@@ -305,7 +305,7 @@
         Self { sse: max_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_max(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vmaxq_s8(self.neon, rhs.neon) }}
       } else {
         self.simd_lt(rhs).select(rhs, self)
@@ -320,7 +320,7 @@
         Self { sse: min_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_min(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vminq_s8(self.neon, rhs.neon) }}
       } else {
         self.simd_lt(rhs).select(self, rhs)
@@ -364,7 +364,7 @@
         let rhs = i8x16_shuffle::<1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0>(max, max);
         let max = i8x16_max(max, rhs);
         i8x16_extract_lane::<0>(max)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Use `transmute` instead of `cast` because `int8x16_t` does not
           // implement `bytemuck::Pod`.
@@ -421,7 +421,7 @@
         let rhs = i8x16_shuffle::<1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0>(min, min);
         let min = i8x16_min(min, rhs);
         i8x16_extract_lane::<0>(min)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Use `transmute` instead of `cast` because `int8x16_t` does not
           // implement `bytemuck::Pod`.
@@ -448,7 +448,7 @@
     // to `i16` or `i32` then converting back after multiplication, but that may
     // not actually be faster than auto-vectorization.
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -489,7 +489,7 @@
     pick! {
       if #[cfg(target_feature="simd128")] {
         if rhs < 8 { Self { simd: i8x16_shr(self.simd, rhs) } } else { self.is_negative() }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -527,7 +527,7 @@
         Self { sse: add_saturating_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_add_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vqaddq_s8(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -559,7 +559,7 @@
         Self { sse: sub_saturating_i8_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_sub_sat(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqsubq_s8(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -597,7 +597,7 @@
     #[inline]
     pub fn widening_mul(self, rhs: Self) -> i16x16 {
       pick! {
-        if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+        if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
           unsafe {
             let low_wide_mul = vmull_s8(vget_low_s8(self.neon), vget_low_s8(rhs.neon));
             let high_wide_mul = vmull_s8(vget_high_s8(self.neon), vget_high_s8(rhs.neon));
@@ -637,7 +637,7 @@
   #[inline]
   pub fn mul_keep_low_high(self, rhs: Self) -> (u8x16, i8x16) {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_s8_s16(
             vmull_s8(vget_low_s8(self.neon), vget_low_s8(rhs.neon)),
@@ -723,7 +723,7 @@
   #[inline]
   pub fn mul_keep_high(self, rhs: Self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           let low_wide_mul = vreinterpretq_s8_s16(
             vmull_s8(vget_low_s8(self.neon), vget_low_s8(rhs.neon)),
@@ -767,7 +767,7 @@
         Self { sse: abs_i8_m128i(self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i8x16_abs(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vabsq_s8(self.neon) }}
       } else {
         let arr: [i8; 16] = cast(self);
@@ -796,7 +796,7 @@
   #[inline]
   pub fn is_positive(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vreinterpretq_s8_u8(vcgtzq_s8(self.neon)) } }
       } else {
         self.simd_gt(Self::ZERO)
@@ -807,7 +807,7 @@
   #[inline]
   pub fn is_negative(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vreinterpretq_s8_u8(vcltzq_s8(self.neon)) } }
       } else {
         self.simd_lt(Self::ZERO)
@@ -831,7 +831,7 @@
         i8x16 { sse: pack_i16_to_i8_m128i( extract_m128i_from_m256i::<0>(v.avx2), extract_m128i_from_m256i::<1>(v.avx2))  }
       } else if #[cfg(target_feature="sse2")] {
         i8x16 { sse: pack_i16_to_i8_m128i( v.a.sse, v.b.sse ) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         use core::arch::aarch64::*;
 
         unsafe {
@@ -928,7 +928,7 @@
         unsafe { Self { sse: load_unaligned_m128i( &*(input.as_ptr() as * const [u8;16]) ) } }
       } else if #[cfg(target_feature="simd128")] {
         unsafe { Self { simd: v128_load(input.as_ptr() as *const v128 ) } }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vld1q_s8( input.as_ptr() as *const i8 ) } }
       } else {
         // 2018 edition doesn't have try_into
