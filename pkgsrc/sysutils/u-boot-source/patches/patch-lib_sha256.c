$NetBSD$

--- a/lib/sha256.c
+++ b/lib/sha256.c
@@ -1,4 +1,4 @@
-// SPDX-License-Identifier: GPL-2.0+
+// SPDX-License-Identifier: GPL-2.0+ AND BSD-3-Clause
 /*
  * FIPS-180-2 compliant SHA-256 implementation
  *
@@ -12,6 +12,14 @@
 #include <u-boot/sha256.h>
 
 #include <linux/compiler_attributes.h>
+
+#ifdef USE_HOSTCC
+#define SHA256_COMPACT 0
+#elif CONFIG_IS_ENABLED(SHA256_SMALL)
+#define SHA256_COMPACT 1
+#else
+#define SHA256_COMPACT 0
+#endif
 
 const uint8_t sha256_der_prefix[SHA256_DER_LEN] = {
 	0x30, 0x31, 0x30, 0x0d, 0x06, 0x09, 0x60, 0x86,
@@ -53,6 +61,127 @@
 	ctx->state[6] = 0x1F83D9AB;
 	ctx->state[7] = 0x5BE0CD19;
 }
+
+/* Compact-round design follows the BSD sha2 implementation. */
+/*
+ * sha2.c
+ *
+ * Version 1.0.0beta1
+ *
+ * Written by Aaron D. Gifford <me@aarongifford.com>
+ *
+ * Copyright 2000 Aaron D. Gifford.  All rights reserved.
+ *
+ * Redistribution and use in source and binary forms, with or without
+ * modification, are permitted provided that the following conditions
+ * are met:
+ * 1. Redistributions of source code must retain the above copyright
+ *    notice, this list of conditions and the following disclaimer.
+ * 2. Redistributions in binary form must reproduce the above copyright
+ *    notice, this list of conditions and the following disclaimer in the
+ *    documentation and/or other materials provided with the distribution.
+ * 3. Neither the name of the copyright holder nor the names of contributors
+ *    may be used to endorse or promote products derived from this software
+ *    without specific prior written permission.
+ *
+ * THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) AND CONTRIBUTOR(S) ``AS IS'' AND
+ * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
+ * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
+ * ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR(S) OR CONTRIBUTOR(S) BE LIABLE
+ * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
+ * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
+ * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
+ * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
+ * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
+ * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
+ * SUCH DAMAGE.
+ *
+ */
+#define SHA256_K00 0x428A2F98U
+#define SHA256_K01 0x71374491U
+#define SHA256_K02 0xB5C0FBCFU
+#define SHA256_K03 0xE9B5DBA5U
+#define SHA256_K04 0x3956C25BU
+#define SHA256_K05 0x59F111F1U
+#define SHA256_K06 0x923F82A4U
+#define SHA256_K07 0xAB1C5ED5U
+#define SHA256_K08 0xD807AA98U
+#define SHA256_K09 0x12835B01U
+#define SHA256_K10 0x243185BEU
+#define SHA256_K11 0x550C7DC3U
+#define SHA256_K12 0x72BE5D74U
+#define SHA256_K13 0x80DEB1FEU
+#define SHA256_K14 0x9BDC06A7U
+#define SHA256_K15 0xC19BF174U
+#define SHA256_K16 0xE49B69C1U
+#define SHA256_K17 0xEFBE4786U
+#define SHA256_K18 0x0FC19DC6U
+#define SHA256_K19 0x240CA1CCU
+#define SHA256_K20 0x2DE92C6FU
+#define SHA256_K21 0x4A7484AAU
+#define SHA256_K22 0x5CB0A9DCU
+#define SHA256_K23 0x76F988DAU
+#define SHA256_K24 0x983E5152U
+#define SHA256_K25 0xA831C66DU
+#define SHA256_K26 0xB00327C8U
+#define SHA256_K27 0xBF597FC7U
+#define SHA256_K28 0xC6E00BF3U
+#define SHA256_K29 0xD5A79147U
+#define SHA256_K30 0x06CA6351U
+#define SHA256_K31 0x14292967U
+#define SHA256_K32 0x27B70A85U
+#define SHA256_K33 0x2E1B2138U
+#define SHA256_K34 0x4D2C6DFCU
+#define SHA256_K35 0x53380D13U
+#define SHA256_K36 0x650A7354U
+#define SHA256_K37 0x766A0ABBU
+#define SHA256_K38 0x81C2C92EU
+#define SHA256_K39 0x92722C85U
+#define SHA256_K40 0xA2BFE8A1U
+#define SHA256_K41 0xA81A664BU
+#define SHA256_K42 0xC24B8B70U
+#define SHA256_K43 0xC76C51A3U
+#define SHA256_K44 0xD192E819U
+#define SHA256_K45 0xD6990624U
+#define SHA256_K46 0xF40E3585U
+#define SHA256_K47 0x106AA070U
+#define SHA256_K48 0x19A4C116U
+#define SHA256_K49 0x1E376C08U
+#define SHA256_K50 0x2748774CU
+#define SHA256_K51 0x34B0BCB5U
+#define SHA256_K52 0x391C0CB3U
+#define SHA256_K53 0x4ED8AA4AU
+#define SHA256_K54 0x5B9CCA4FU
+#define SHA256_K55 0x682E6FF3U
+#define SHA256_K56 0x748F82EEU
+#define SHA256_K57 0x78A5636FU
+#define SHA256_K58 0x84C87814U
+#define SHA256_K59 0x8CC70208U
+#define SHA256_K60 0x90BEFFFAU
+#define SHA256_K61 0xA4506CEBU
+#define SHA256_K62 0xBEF9A3F7U
+#define SHA256_K63 0xC67178F2U
+
+#if SHA256_COMPACT
+static const uint32_t sha256_round_constants[64] = {
+	SHA256_K00, SHA256_K01, SHA256_K02, SHA256_K03,
+	SHA256_K04, SHA256_K05, SHA256_K06, SHA256_K07,
+	SHA256_K08, SHA256_K09, SHA256_K10, SHA256_K11,
+	SHA256_K12, SHA256_K13, SHA256_K14, SHA256_K15,
+	SHA256_K16, SHA256_K17, SHA256_K18, SHA256_K19,
+	SHA256_K20, SHA256_K21, SHA256_K22, SHA256_K23,
+	SHA256_K24, SHA256_K25, SHA256_K26, SHA256_K27,
+	SHA256_K28, SHA256_K29, SHA256_K30, SHA256_K31,
+	SHA256_K32, SHA256_K33, SHA256_K34, SHA256_K35,
+	SHA256_K36, SHA256_K37, SHA256_K38, SHA256_K39,
+	SHA256_K40, SHA256_K41, SHA256_K42, SHA256_K43,
+	SHA256_K44, SHA256_K45, SHA256_K46, SHA256_K47,
+	SHA256_K48, SHA256_K49, SHA256_K50, SHA256_K51,
+	SHA256_K52, SHA256_K53, SHA256_K54, SHA256_K55,
+	SHA256_K56, SHA256_K57, SHA256_K58, SHA256_K59,
+	SHA256_K60, SHA256_K61, SHA256_K62, SHA256_K63,
+};
+#endif
 
 static void sha256_process_one(sha256_context *ctx, const uint8_t data[64])
 {
@@ -110,70 +239,86 @@
 	G = ctx->state[6];
 	H = ctx->state[7];
 
-	P(A, B, C, D, E, F, G, H, W[0], 0x428A2F98);
-	P(H, A, B, C, D, E, F, G, W[1], 0x71374491);
-	P(G, H, A, B, C, D, E, F, W[2], 0xB5C0FBCF);
-	P(F, G, H, A, B, C, D, E, W[3], 0xE9B5DBA5);
-	P(E, F, G, H, A, B, C, D, W[4], 0x3956C25B);
-	P(D, E, F, G, H, A, B, C, W[5], 0x59F111F1);
-	P(C, D, E, F, G, H, A, B, W[6], 0x923F82A4);
-	P(B, C, D, E, F, G, H, A, W[7], 0xAB1C5ED5);
-	P(A, B, C, D, E, F, G, H, W[8], 0xD807AA98);
-	P(H, A, B, C, D, E, F, G, W[9], 0x12835B01);
-	P(G, H, A, B, C, D, E, F, W[10], 0x243185BE);
-	P(F, G, H, A, B, C, D, E, W[11], 0x550C7DC3);
-	P(E, F, G, H, A, B, C, D, W[12], 0x72BE5D74);
-	P(D, E, F, G, H, A, B, C, W[13], 0x80DEB1FE);
-	P(C, D, E, F, G, H, A, B, W[14], 0x9BDC06A7);
-	P(B, C, D, E, F, G, H, A, W[15], 0xC19BF174);
-	P(A, B, C, D, E, F, G, H, R(16), 0xE49B69C1);
-	P(H, A, B, C, D, E, F, G, R(17), 0xEFBE4786);
-	P(G, H, A, B, C, D, E, F, R(18), 0x0FC19DC6);
-	P(F, G, H, A, B, C, D, E, R(19), 0x240CA1CC);
-	P(E, F, G, H, A, B, C, D, R(20), 0x2DE92C6F);
-	P(D, E, F, G, H, A, B, C, R(21), 0x4A7484AA);
-	P(C, D, E, F, G, H, A, B, R(22), 0x5CB0A9DC);
-	P(B, C, D, E, F, G, H, A, R(23), 0x76F988DA);
-	P(A, B, C, D, E, F, G, H, R(24), 0x983E5152);
-	P(H, A, B, C, D, E, F, G, R(25), 0xA831C66D);
-	P(G, H, A, B, C, D, E, F, R(26), 0xB00327C8);
-	P(F, G, H, A, B, C, D, E, R(27), 0xBF597FC7);
-	P(E, F, G, H, A, B, C, D, R(28), 0xC6E00BF3);
-	P(D, E, F, G, H, A, B, C, R(29), 0xD5A79147);
-	P(C, D, E, F, G, H, A, B, R(30), 0x06CA6351);
-	P(B, C, D, E, F, G, H, A, R(31), 0x14292967);
-	P(A, B, C, D, E, F, G, H, R(32), 0x27B70A85);
-	P(H, A, B, C, D, E, F, G, R(33), 0x2E1B2138);
-	P(G, H, A, B, C, D, E, F, R(34), 0x4D2C6DFC);
-	P(F, G, H, A, B, C, D, E, R(35), 0x53380D13);
-	P(E, F, G, H, A, B, C, D, R(36), 0x650A7354);
-	P(D, E, F, G, H, A, B, C, R(37), 0x766A0ABB);
-	P(C, D, E, F, G, H, A, B, R(38), 0x81C2C92E);
-	P(B, C, D, E, F, G, H, A, R(39), 0x92722C85);
-	P(A, B, C, D, E, F, G, H, R(40), 0xA2BFE8A1);
-	P(H, A, B, C, D, E, F, G, R(41), 0xA81A664B);
-	P(G, H, A, B, C, D, E, F, R(42), 0xC24B8B70);
-	P(F, G, H, A, B, C, D, E, R(43), 0xC76C51A3);
-	P(E, F, G, H, A, B, C, D, R(44), 0xD192E819);
-	P(D, E, F, G, H, A, B, C, R(45), 0xD6990624);
-	P(C, D, E, F, G, H, A, B, R(46), 0xF40E3585);
-	P(B, C, D, E, F, G, H, A, R(47), 0x106AA070);
-	P(A, B, C, D, E, F, G, H, R(48), 0x19A4C116);
-	P(H, A, B, C, D, E, F, G, R(49), 0x1E376C08);
-	P(G, H, A, B, C, D, E, F, R(50), 0x2748774C);
-	P(F, G, H, A, B, C, D, E, R(51), 0x34B0BCB5);
-	P(E, F, G, H, A, B, C, D, R(52), 0x391C0CB3);
-	P(D, E, F, G, H, A, B, C, R(53), 0x4ED8AA4A);
-	P(C, D, E, F, G, H, A, B, R(54), 0x5B9CCA4F);
-	P(B, C, D, E, F, G, H, A, R(55), 0x682E6FF3);
-	P(A, B, C, D, E, F, G, H, R(56), 0x748F82EE);
-	P(H, A, B, C, D, E, F, G, R(57), 0x78A5636F);
-	P(G, H, A, B, C, D, E, F, R(58), 0x84C87814);
-	P(F, G, H, A, B, C, D, E, R(59), 0x8CC70208);
-	P(E, F, G, H, A, B, C, D, R(60), 0x90BEFFFA);
-	P(D, E, F, G, H, A, B, C, R(61), 0xA4506CEB);
-	P(C, D, E, F, G, H, A, B, R(62), 0xBEF9A3F7);
-	P(B, C, D, E, F, G, H, A, R(63), 0xC67178F2);
+#if SHA256_COMPACT
+	/* The same rounds, iterated in groups of eight to reduce code size. */
+	for (unsigned int i = 0; i < 64; i += 8) {
+#define SMALL_W(n) ((n) < 16 ? W[n] : R(n))
+		P(A, B, C, D, E, F, G, H, SMALL_W(i), sha256_round_constants[i]);
+		P(H, A, B, C, D, E, F, G, SMALL_W(i + 1), sha256_round_constants[i + 1]);
+		P(G, H, A, B, C, D, E, F, SMALL_W(i + 2), sha256_round_constants[i + 2]);
+		P(F, G, H, A, B, C, D, E, SMALL_W(i + 3), sha256_round_constants[i + 3]);
+		P(E, F, G, H, A, B, C, D, SMALL_W(i + 4), sha256_round_constants[i + 4]);
+		P(D, E, F, G, H, A, B, C, SMALL_W(i + 5), sha256_round_constants[i + 5]);
+		P(C, D, E, F, G, H, A, B, SMALL_W(i + 6), sha256_round_constants[i + 6]);
+		P(B, C, D, E, F, G, H, A, SMALL_W(i + 7), sha256_round_constants[i + 7]);
+#undef SMALL_W
+	}
+#else
+	P(A, B, C, D, E, F, G, H, W[0], SHA256_K00);
+	P(H, A, B, C, D, E, F, G, W[1], SHA256_K01);
+	P(G, H, A, B, C, D, E, F, W[2], SHA256_K02);
+	P(F, G, H, A, B, C, D, E, W[3], SHA256_K03);
+	P(E, F, G, H, A, B, C, D, W[4], SHA256_K04);
+	P(D, E, F, G, H, A, B, C, W[5], SHA256_K05);
+	P(C, D, E, F, G, H, A, B, W[6], SHA256_K06);
+	P(B, C, D, E, F, G, H, A, W[7], SHA256_K07);
+	P(A, B, C, D, E, F, G, H, W[8], SHA256_K08);
+	P(H, A, B, C, D, E, F, G, W[9], SHA256_K09);
+	P(G, H, A, B, C, D, E, F, W[10], SHA256_K10);
+	P(F, G, H, A, B, C, D, E, W[11], SHA256_K11);
+	P(E, F, G, H, A, B, C, D, W[12], SHA256_K12);
+	P(D, E, F, G, H, A, B, C, W[13], SHA256_K13);
+	P(C, D, E, F, G, H, A, B, W[14], SHA256_K14);
+	P(B, C, D, E, F, G, H, A, W[15], SHA256_K15);
+	P(A, B, C, D, E, F, G, H, R(16), SHA256_K16);
+	P(H, A, B, C, D, E, F, G, R(17), SHA256_K17);
+	P(G, H, A, B, C, D, E, F, R(18), SHA256_K18);
+	P(F, G, H, A, B, C, D, E, R(19), SHA256_K19);
+	P(E, F, G, H, A, B, C, D, R(20), SHA256_K20);
+	P(D, E, F, G, H, A, B, C, R(21), SHA256_K21);
+	P(C, D, E, F, G, H, A, B, R(22), SHA256_K22);
+	P(B, C, D, E, F, G, H, A, R(23), SHA256_K23);
+	P(A, B, C, D, E, F, G, H, R(24), SHA256_K24);
+	P(H, A, B, C, D, E, F, G, R(25), SHA256_K25);
+	P(G, H, A, B, C, D, E, F, R(26), SHA256_K26);
+	P(F, G, H, A, B, C, D, E, R(27), SHA256_K27);
+	P(E, F, G, H, A, B, C, D, R(28), SHA256_K28);
+	P(D, E, F, G, H, A, B, C, R(29), SHA256_K29);
+	P(C, D, E, F, G, H, A, B, R(30), SHA256_K30);
+	P(B, C, D, E, F, G, H, A, R(31), SHA256_K31);
+	P(A, B, C, D, E, F, G, H, R(32), SHA256_K32);
+	P(H, A, B, C, D, E, F, G, R(33), SHA256_K33);
+	P(G, H, A, B, C, D, E, F, R(34), SHA256_K34);
+	P(F, G, H, A, B, C, D, E, R(35), SHA256_K35);
+	P(E, F, G, H, A, B, C, D, R(36), SHA256_K36);
+	P(D, E, F, G, H, A, B, C, R(37), SHA256_K37);
+	P(C, D, E, F, G, H, A, B, R(38), SHA256_K38);
+	P(B, C, D, E, F, G, H, A, R(39), SHA256_K39);
+	P(A, B, C, D, E, F, G, H, R(40), SHA256_K40);
+	P(H, A, B, C, D, E, F, G, R(41), SHA256_K41);
+	P(G, H, A, B, C, D, E, F, R(42), SHA256_K42);
+	P(F, G, H, A, B, C, D, E, R(43), SHA256_K43);
+	P(E, F, G, H, A, B, C, D, R(44), SHA256_K44);
+	P(D, E, F, G, H, A, B, C, R(45), SHA256_K45);
+	P(C, D, E, F, G, H, A, B, R(46), SHA256_K46);
+	P(B, C, D, E, F, G, H, A, R(47), SHA256_K47);
+	P(A, B, C, D, E, F, G, H, R(48), SHA256_K48);
+	P(H, A, B, C, D, E, F, G, R(49), SHA256_K49);
+	P(G, H, A, B, C, D, E, F, R(50), SHA256_K50);
+	P(F, G, H, A, B, C, D, E, R(51), SHA256_K51);
+	P(E, F, G, H, A, B, C, D, R(52), SHA256_K52);
+	P(D, E, F, G, H, A, B, C, R(53), SHA256_K53);
+	P(C, D, E, F, G, H, A, B, R(54), SHA256_K54);
+	P(B, C, D, E, F, G, H, A, R(55), SHA256_K55);
+	P(A, B, C, D, E, F, G, H, R(56), SHA256_K56);
+	P(H, A, B, C, D, E, F, G, R(57), SHA256_K57);
+	P(G, H, A, B, C, D, E, F, R(58), SHA256_K58);
+	P(F, G, H, A, B, C, D, E, R(59), SHA256_K59);
+	P(E, F, G, H, A, B, C, D, R(60), SHA256_K60);
+	P(D, E, F, G, H, A, B, C, R(61), SHA256_K61);
+	P(C, D, E, F, G, H, A, B, R(62), SHA256_K62);
+	P(B, C, D, E, F, G, H, A, R(63), SHA256_K63);
+#endif
 
 	ctx->state[0] += A;
 	ctx->state[1] += B;
