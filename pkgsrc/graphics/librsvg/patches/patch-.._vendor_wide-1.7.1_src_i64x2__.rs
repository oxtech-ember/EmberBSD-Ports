$NetBSD: patch-.._vendor_wide-0.7.33_src_i64x2__.rs,v 1.1 2025/12/08 12:40:17 adam Exp $

Do not use little-endian-only NEON intrinsics on big-endian AArch64.
Origin: pkgsrc big-endian patches; refreshed for wide-1.7.1 by EmberBSD
(AI-assisted). Newly added matching branches use the same scalar fallback.
Not submitted upstream; big-endian execution has not been validated here.

--- ../vendor/wide-1.7.1/src/i64x2_.rs.orig
+++ ../vendor/wide-1.7.1/src/i64x2_.rs
@@ -37,7 +37,7 @@
     }
 
     impl Eq for i64x2 { }
-  } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+  } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
     use core::arch::aarch64::*;
 
     /// A SIMD vector with two elements of type [`i64`].
@@ -103,7 +103,7 @@
         Self { sse: cmp_gt_mask_i64_m128i( rhs.sse, self.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_lt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_s64_u64(vcltq_s64(self.neon, rhs.neon)) }}
       } else {
         let s: [i64;2] = cast(self);
@@ -123,7 +123,7 @@
         Self { sse: cmp_gt_mask_i64_m128i(self.sse, rhs.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_gt(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vreinterpretq_s64_u64(vcgtq_s64(self.neon, rhs.neon)) }}
       } else {
         let s: [i64;2] = cast(self);
@@ -143,7 +143,7 @@
         !self.simd_gt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_le(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_gt(rhs)
       } else {
         let s: [i64;2] = cast(self);
@@ -163,7 +163,7 @@
         !self.simd_lt(rhs)
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_ge(self.simd, rhs.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         !self.simd_lt(rhs)
       } else {
         let s: [i64;2] = cast(self);
@@ -179,7 +179,7 @@
   #[inline]
   fn shr(self, rhs: u64x2) -> Self::Output {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // mask the shift count to 63 to have same behavior on all platforms
           // no right shift, have to pass negative value to left shift on neon
@@ -228,7 +228,7 @@
       if #[cfg(any(target_feature="sse2", target_feature="simd128"))] {
         let array: [i64; 2] = cast(self);
         array[0].max(array[1])
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vgetq_lane_s64(self.neon, 0).max(vgetq_lane_s64(self.neon, 1)) }
       } else {
         self.arr[0].max(self.arr[1])
@@ -242,7 +242,7 @@
       if #[cfg(any(target_feature="sse2", target_feature="simd128"))] {
         let array: [i64; 2] = cast(self);
         array[0].min(array[1])
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { vgetq_lane_s64(self.neon, 0).min(vgetq_lane_s64(self.neon, 1)) }
       } else {
         self.arr[0].min(self.arr[1])
@@ -253,7 +253,7 @@
   #[inline]
   pub fn unbounded_shr(self, rhs: u64x2) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         unsafe {
           // Negate `rhs` because there is no direct shift-right intrinsic, and
           // restrict it to prevent overflow.
@@ -296,7 +296,7 @@
 
         // If overflow occurs return `MAX` if positive or `MIN` if negative.
         overflow.select(Self::MAX ^ negative, result)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqaddq_s64(self.neon, rhs.neon) } }
       } else {
         Self {
@@ -319,7 +319,7 @@
 
         // If overflow occurs return `MAX` if positive or `MIN` if negative.
         overflow.select(Self::MAX ^ negative, result)
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe { Self { neon: vqsubq_s64(self.neon, rhs.neon) } }
       } else {
         Self {
@@ -397,7 +397,7 @@
       // x86 doesn't have this builtin
       if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_abs(self.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))]{
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))]{
         unsafe {Self { neon: vabsq_s64(self.neon) }}
       } else {
         let arr: [i64; 2] = cast(self);
@@ -413,7 +413,7 @@
   #[inline]
   pub fn is_positive(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vreinterpretq_s64_u64(vcgtzq_s64(self.neon)) } }
       } else {
         self.simd_gt(Self::ZERO)
@@ -424,7 +424,7 @@
   #[inline]
   pub fn is_negative(self) -> Self {
     pick! {
-      if #[cfg(all(target_feature="neon", target_arch="aarch64"))] {
+      if #[cfg(all(target_feature="neon", target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vreinterpretq_s64_u64(vcltzq_s64(self.neon)) } }
       } else {
         self.simd_lt(Self::ZERO)
@@ -456,7 +456,7 @@
         Self { sse: unpack_low_i64_m128i(self.sse, b.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_shuffle::<0, 2>(self.simd, b.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vzip1q_s64(self.neon, b.neon) } }
       } else {
         Self::new([self.as_array()[0], b.as_array()[0]])
@@ -474,7 +474,7 @@
         Self { sse: unpack_high_i64_m128i(self.sse, b.sse) }
       } else if #[cfg(target_feature="simd128")] {
         Self { simd: i64x2_shuffle::<1, 3>(self.simd, b.simd) }
-      } else if #[cfg(all(target_feature="neon",target_arch="aarch64"))] {
+      } else if #[cfg(all(target_feature="neon",target_arch="aarch64",target_endian="little"))] {
         Self { neon: unsafe { vzip2q_s64(self.neon, b.neon) } }
       } else {
         Self::new([self.as_array()[1], b.as_array()[1]])
