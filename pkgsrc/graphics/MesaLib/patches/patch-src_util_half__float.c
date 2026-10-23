Origin: EmberBSD; AI-assisted Mesa 26.2.4 adaptation.
Status: local; not submitted upstream.

Preserve binary16 subnormals when the process FP state flushes binary32
subnormals. All binary16 nonzero values are representable as normal binary32
values; integer normalization avoids a flushed floating-point intermediate.
The upstream exhaustive 65536-value u_half_test detected this on UTM/aarch64.

--- src/util/half_float.c.orig
+++ src/util/half_float.c
@@ -142,29 +142,34 @@
 float
 _mesa_half_to_float_slow(uint16_t val)
 {
-   union fi infnan;
-   union fi magic;
-   union fi f32;
+   union fi result;
+   uint32_t mantissa = val & 0x3ff;
+   uint32_t exponent = (val >> 10) & 0x1f;
+   uint32_t bits;
+
+   /* Every nonzero binary16 subnormal is normal in binary32. Normalize
+    * with integer operations: a floating-point intermediate can be flushed
+    * to zero by the caller's FP state before it is scaled to binary32.
+    */
+   if (exponent == 0) {
+      bits = 0;
+      if (mantissa != 0) {
+         int unbiased = -14;
+         while ((mantissa & 0x400) == 0) {
+            mantissa <<= 1;
+            unbiased--;
+         }
+         bits = ((uint32_t)(unbiased + 127) << 23) |
+                ((mantissa & 0x3ff) << 13);
+      }
+   } else if (exponent == 31) {
+      bits = 0x7f800000 | (mantissa << 13);
+   } else {
+      bits = ((exponent + 112) << 23) | (mantissa << 13);
+   }
 
-   infnan.ui = 0x8f << 23;
-   infnan.f = 65536.0f;
-   magic.ui  = 0xef << 23;
-
-   /* Exponent / Mantissa */
-   f32.ui = (val & 0x7fff) << 13;
-
-   /* Adjust */
-   f32.f *= magic.f;
-   /* XXX: The magic mul relies on denorms being available */
-
-   /* Inf / NaN */
-   if (f32.f >= infnan.f)
-      f32.ui |= 0xff << 23;
-
-   /* Sign */
-   f32.ui |= (uint32_t)(val & 0x8000) << 16;
-
-   return f32.f;
+   result.ui = bits | ((uint32_t)(val & 0x8000) << 16);
+   return result.f;
 }
 
 /**
