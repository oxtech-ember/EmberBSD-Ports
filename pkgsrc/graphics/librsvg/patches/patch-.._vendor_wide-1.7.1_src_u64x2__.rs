$NetBSD: patch-.._vendor_wide-0.7.33_src_u64x2__.rs,v 1.1 2025/12/08 12:40:17 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/u64x2_.rs.orig
+++ ../vendor/wide-1.7.1/src/u64x2_.rs
@@ -37,7 +37,7 @@
     }
 
     impl Eq for u64x2 { }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
     use core::arch::aarch64::*;
 
     /// A SIMD vector with two elements of type [`u64`].
@@ -107,7 +107,7 @@
         Self { sse: add_i64_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u64x2_add(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vaddq_u64(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -125,7 +125,7 @@
         Self { sse: sub_i64_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u64x2_sub(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vsubq_u64(self.neon, rhs.neon) } }
       } else {
         Self { arr: [
@@ -160,7 +160,7 @@
         Self { sse: bitand_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_and(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vandq_u64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -178,7 +178,7 @@
         Self { sse: bitor_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_or(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vorrq_u64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -196,7 +196,7 @@
         Self { sse: bitxor_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_xor(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: veorq_u64(self.neon, rhs.neon) }}
       } else {
         Self { arr: [
@@ -214,7 +214,7 @@
         Self { sse: cmp_eq_mask_i64_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u64x2_eq(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vceqq_u64(self.neon, rhs.neon) } }
       } else {
         let s: [u64;2] = cast(self);
@@ -234,7 +234,7 @@
         !self.simd_eq(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u64x2_ne(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_eq(rhs)
       } else {
         let s: [u64;2] = cast(self);
@@ -260,7 +260,7 @@
         // no unsigned gt so inverting the high bit will get the correct result
         let highbit = u64x2::splat(1 << 63);
         Self { sse: cmp_gt_mask_i64_m128i((self ^ highbit).sse, (rhs ^ highbit).sse) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vcgtq_u64(self.neon, rhs.neon) }}
       } else {
         // u64x2_gt on WASM is not a thing. https://github.com/WebAssembly/simd/pull/414
@@ -279,7 +279,7 @@
     pick! {
       if #[cfg(target_feature="sse4.1")] {
         !self.simd_gt(rhs)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_gt(rhs)
       } else {
         let s: [u64;2] = cast(self);
@@ -297,7 +297,7 @@
     pick! {
       if #[cfg(target_feature="sse4.1")] {
         !self.simd_lt(rhs)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_lt(rhs)
       } else {
         let s: [u64;2] = cast(self);
@@ -316,7 +316,7 @@
       if #[cfg(any(target_feature="sse2", target_feature="simd128"))] {
         let array: [u64; 2] = cast(self);
         array[0].wrapping_add(array[1])
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vgetq_lane_u64(self.neon, 0).wrapping_add(vgetq_lane_u64(self.neon, 1)) }
       } else {
         self.arr[0].wrapping_add(self.arr[1])
@@ -330,7 +330,7 @@
       if #[cfg(any(target_feature="sse2", target_feature="simd128"))] {
         let array: [u64; 2] = cast(self);
         array[0].wrapping_mul(array[1])
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vgetq_lane_u64(self.neon, 0).wrapping_mul(vgetq_lane_u64(self.neon, 1)) }
       } else {
         self.arr[0].wrapping_mul(self.arr[1])
@@ -350,7 +350,7 @@
         }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_one.simd, if_zero.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_u64(self.neon, if_one.neon, if_zero.neon) }}
       } else {
         generic_bit_blend(self, if_one, if_zero)
@@ -365,7 +365,7 @@
         Self { sse: blend_varying_i8_m128i(if_false.sse, if_true.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: v128_bitselect(if_true.simd, if_false.simd, self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vbslq_u64(self.neon, if_true.neon, if_false.neon) }}
       } else {
         generic_bit_blend(self, if_true, if_false)
@@ -436,7 +436,7 @@
         // We can assume that each index is either `0` or `1`, and negating that
         // always gives us either all bits zero or all bits one.
         (-indices).select(e1, e0)
-      } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64"))]{
+      } else if #[cfg(all(target_feature = "neon", target_arch = "aarch64",target_endian="little"))]{
         let e0 = unsafe { Self { neon: vdupq_n_u64(vget_lane_u64::<0>(vget_low_u64(self.neon))) } };
         let e1 = unsafe { Self { neon: vdupq_n_u64(vget_lane_u64::<0>(vget_high_u64(self.neon))) } };
 
@@ -546,7 +546,7 @@
     pick! {
       if #[cfg(any(
         target_feature="sse2",
-        all(target_feature="neon",target_arch="aarch64"),
+        all(target_feature="neon",target_arch="aarch64",target_endian="little"),
         target_feature="simd128",
       ))] {
         // TODO: Remove the casts once unpack functions exist for `Self`.
@@ -569,7 +569,7 @@
         // mask the shift count to 63 to have same behavior on all platforms
         let shift_by = rhs & Self::splat(63);
         Self { sse: shl_each_u64_m128i(self.sse, shift_by.sse) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // mask the shift count to 63 to have same behavior on all platforms
           let shift_by = vreinterpretq_s64_u64(vandq_u64(rhs.neon, vmovq_n_u64(63)));
@@ -596,7 +596,7 @@
         Self { sse: shl_all_u64_m128i(self.sse, shift) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u64x2_shl(self.simd, rhs) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Use `rhs % 64` to perform wrapping shift and not unbounded shift.
         #[expect(clippy::suspicious_arithmetic_impl)]
         unsafe {Self { neon: vshlq_u64(self.neon, vmovq_n_s64(rhs as i64 & 63)) }}
@@ -616,7 +616,7 @@
         // mask the shift count to 63 to have same behavior on all platforms
         let shift_by = rhs & Self::splat(63);
         Self { sse: shr_each_u64_m128i(self.sse, shift_by.sse) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // mask the shift count to 63 to have same behavior on all platforms
           // no right shift, have to pass negative value to left shift on neon
@@ -644,7 +644,7 @@
         Self { sse: shr_all_u64_m128i(self.sse, shift) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: u64x2_shr(self.simd, rhs) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         // Use `rhs % 64` to perform wrapping shift and not unbounded shift.
         #[expect(clippy::suspicious_arithmetic_impl)]
         unsafe {Self { neon: vshlq_u64(self.neon, vmovq_n_s64(-(rhs as i64 & 63))) }}
@@ -673,7 +673,7 @@
       if #[cfg(any(target_feature="sse2", target_feature="simd128"))] {
         let array: [u64; 2] = cast(self);
         array[0].max(array[1])
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vgetq_lane_u64(self.neon, 0).max(vgetq_lane_u64(self.neon, 1)) }
       } else {
         self.arr[0].max(self.arr[1])
@@ -687,7 +687,7 @@
       if #[cfg(any(target_feature="sse2", target_feature="simd128"))] {
         let array: [u64; 2] = cast(self);
         array[0].min(array[1])
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vgetq_lane_u64(self.neon, 0).min(vgetq_lane_u64(self.neon, 1)) }
       } else {
         self.arr[0].min(self.arr[1])
@@ -700,7 +700,7 @@
     pick! {
       if #[cfg(target_feature="avx2")] {
         Self { sse: shl_each_u64_m128i(self.sse, rhs.sse) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // The intrinsic has different semantics so we need to mask ourselves.
           Self { neon: vshlq_u64(self.neon, vreinterpretq_s64_u64(rhs.neon)) } & rhs.simd_lt(64)
@@ -721,7 +721,7 @@
       } else if #[cfg(target_feature="simd128")] {
         // The intrinsic performs wrapping shift so we need to mask the result.
         Self { simd: u64x2_shl(self.simd, rhs) } & Self::splat(rhs as u64).simd_lt(64)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vshlq_u64(self.neon, vmovq_n_s64(rhs.min(64) as i64)) } }
       } else {
         Self { arr: [
@@ -737,7 +737,7 @@
     pick! {
       if #[cfg(target_feature="avx2")] {
         Self { sse: shr_each_u64_m128i(self.sse, rhs.sse) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // mask to hide `rhs` overflow.
@@ -758,7 +758,7 @@
         Self { sse: shr_all_u64_m128i(self.sse, cast([rhs as u64, 0])) }
       } else if #[cfg(target_feature="simd128")] {
         if rhs < 64 { Self { simd: u64x2_shr(self.simd, rhs) } } else { Self::ZERO }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -783,7 +783,7 @@
         let overflow = result.simd_lt(self);
         // Return `MAX` (all bits set) if overflow occurs.
         result | overflow
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqaddq_u64(self.neon, rhs.neon) } }
       } else {
         Self {
@@ -804,7 +804,7 @@
         let no_overflow = result.simd_le(self);
         // Return `0` (no bits set) if overflow occurs.
         result & no_overflow
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqsubq_u64(self.neon, rhs.neon) } }
       } else {
         Self {
@@ -916,7 +916,7 @@
         Self { sse: unpack_low_i64_m128i(self.sse, b.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_shuffle::<0, 2>(self.simd, b.simd) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vzip1q_u64(self.neon, b.neon) } }
       } else {
         Self::new([self.as_array()[0], b.as_array()[0]])
@@ -933,7 +933,7 @@
         Self { sse: unpack_high_i64_m128i(self.sse, b.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_shuffle::<1, 3>(self.simd, b.simd) }
-      } else if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vzip2q_u64(self.neon, b.neon) } }
       } else {
         Self::new([self.as_array()[1], b.as_array()[1]])
