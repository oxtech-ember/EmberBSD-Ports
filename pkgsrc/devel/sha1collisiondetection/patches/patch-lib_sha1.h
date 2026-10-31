$NetBSD$

Bring the release library to upstream a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988.
https://github.com/cr-marcstevens/sha1collisiondetection/compare/stable-v1.0.3...a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988

--- lib/sha1.h.orig
+++ lib/sha1.h
@@ -12,38 +12,30 @@
 extern "C" {
 #endif
 
+#ifndef SHA1DC_NO_STANDARD_INCLUDES
 #include <stdint.h>
+#endif
 
-/* uses SHA-1 message expansion to expand the first 16 words of W[] to 80 words */
-/* void sha1_message_expansion(uint32_t W[80]); */
-
-/* sha-1 compression function; first version takes a message block pre-parsed as 16 32-bit integers, second version takes an already expanded message) */
-/* void sha1_compression(uint32_t ihv[5], const uint32_t m[16]);
-void sha1_compression_W(uint32_t ihv[5], const uint32_t W[80]); */
-
-/* same as sha1_compression_W, but additionally store intermediate states */
+/* sha-1 compression function that takes an already expanded message, and additionally store intermediate states */
 /* only stores states ii (the state between step ii-1 and step ii) when DOSTORESTATEii is defined in ubc_check.h */
 void sha1_compression_states(uint32_t[5], const uint32_t[16], uint32_t[80], uint32_t[80][5]);
 
 /*
-// function type for sha1_recompression_step_T (uint32_t ihvin[5], uint32_t ihvout[5], const uint32_t me2[80], const uint32_t state[5])
-// where 0 <= T < 80
-//       me2 is an expanded message (the expansion of an original message block XOR'ed with a disturbance vector's message block difference)
-//       state is the internal state (a,b,c,d,e) before step T of the SHA-1 compression function while processing the original message block
-// the function will return:
-//       ihvin: the reconstructed input chaining value
-//       ihvout: the reconstructed output chaining value
+// Function type for sha1_recompression_step_T (uint32_t ihvin[5], uint32_t ihvout[5], const uint32_t me2[80], const uint32_t state[5]).
+// Where 0 <= T < 80
+//       me2 is an expanded message (the expansion of an original message block XOR'ed with a disturbance vector's message block difference.)
+//       state is the internal state (a,b,c,d,e) before step T of the SHA-1 compression function while processing the original message block.
+// The function will return:
+//       ihvin: The reconstructed input chaining value.
+//       ihvout: The reconstructed output chaining value.
 */
 typedef void(*sha1_recompression_type)(uint32_t*, uint32_t*, const uint32_t*, const uint32_t*);
 
-/* table of sha1_recompression_step_0, ... , sha1_recompression_step_79 */
-/* extern sha1_recompression_type sha1_recompression_step[80];*/
-
-/* a callback function type that can be set to be called when a collision block has been found: */
+/* A callback function type that can be set to be called when a collision block has been found: */
 /* void collision_block_callback(uint64_t byteoffset, const uint32_t ihvin1[5], const uint32_t ihvin2[5], const uint32_t m1[80], const uint32_t m2[80]) */
 typedef void(*collision_block_callback)(uint64_t, const uint32_t*, const uint32_t*, const uint32_t*, const uint32_t*);
 
-/* the SHA-1 context */
+/* The SHA-1 context. */
 typedef struct {
 	uint64_t total;
 	uint32_t ihv[5];
@@ -62,30 +54,34 @@
 	uint32_t states[80][5];
 } SHA1_CTX;
 
-/* initialize SHA-1 context */
+/* Initialize SHA-1 context. */
 void SHA1DCInit(SHA1_CTX*);
 
 /*
-// function to enable safe SHA-1 hashing:
-// collision attacks are thwarted by hashing a detected near-collision block 3 times
-// think of it as extending SHA-1 from 80-steps to 240-steps for such blocks:
-//   the best collision attacks against SHA-1 have complexity about 2^60,
-//   thus for 240-steps an immediate lower-bound for the best cryptanalytic attacks would 2^180
-//   an attacker would be better off using a generic birthday search of complexity 2^80
-//
-// enabling safe SHA-1 hashing will result in the correct SHA-1 hash for messages where no collision attack was detected
-// but it will result in a different SHA-1 hash for messages where a collision attack was detected
-// this will automatically invalidate SHA-1 based digital signature forgeries
-// enabled by default
+    Function to enable safe SHA-1 hashing:
+    Collision attacks are thwarted by hashing a detected near-collision block 3 times.
+    Think of it as extending SHA-1 from 80-steps to 240-steps for such blocks:
+        The best collision attacks against SHA-1 have complexity about 2^60,
+        thus for 240-steps an immediate lower-bound for the best cryptanalytic attacks would be 2^180.
+        An attacker would be better off using a generic birthday search of complexity 2^80.
+
+   Enabling safe SHA-1 hashing will result in the correct SHA-1 hash for messages where no collision attack was detected,
+   but it will result in a different SHA-1 hash for messages where a collision attack was detected.
+   This will automatically invalidate SHA-1 based digital signature forgeries.
+   Enabled by default.
 */
 void SHA1DCSetSafeHash(SHA1_CTX*, int);
 
-/* function to disable or enable the use of Unavoidable Bitconditions (provides a significant speed up) */
-/* enabled by default */
+/*
+    Function to disable or enable the use of Unavoidable Bitconditions (provides a significant speed up).
+    Enabled by default
+ */
 void SHA1DCSetUseUBC(SHA1_CTX*, int);
 
-/* function to disable or enable the use of Collision Detection */
-/* enabled by default */
+/*
+    Function to disable or enable the use of Collision Detection.
+    Enabled by default.
+ */
 void SHA1DCSetUseDetectColl(SHA1_CTX*, int);
 
 /* function to disable or enable the detection of reduced-round SHA-1 collisions */
@@ -101,10 +97,14 @@
 
 /* obtain SHA-1 hash from SHA-1 context */
 /* returns: 0 = no collision detected, otherwise = collision found => warn user for active attack */
-int  SHA1DCFinal(unsigned char[20], SHA1_CTX*); 
+int  SHA1DCFinal(unsigned char[20], SHA1_CTX*);
 
 #if defined(__cplusplus)
 }
 #endif
 
+#ifdef SHA1DC_CUSTOM_TRAILING_INCLUDE_SHA1_H
+#include SHA1DC_CUSTOM_TRAILING_INCLUDE_SHA1_H
 #endif
+
+#endif
