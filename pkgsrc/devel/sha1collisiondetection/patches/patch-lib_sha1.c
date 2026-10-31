$NetBSD$

Bring the release library to upstream a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988.
https://github.com/cr-marcstevens/sha1collisiondetection/compare/stable-v1.0.3...a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988

--- lib/sha1.c.orig
+++ lib/sha1.c
@@ -5,16 +5,36 @@
 * https://opensource.org/licenses/MIT
 ***/
 
+#ifndef SHA1DC_NO_STANDARD_INCLUDES
 #include <string.h>
 #include <memory.h>
 #include <stdio.h>
 #include <stdlib.h>
+#ifdef __unix__
+#include <sys/types.h> /* make sure macros like _BIG_ENDIAN visible */
+#endif
+#endif
+
+#ifdef SHA1DC_CUSTOM_INCLUDE_SHA1_C
+#include SHA1DC_CUSTOM_INCLUDE_SHA1_C
+#endif
+
+#ifndef SHA1DC_INIT_SAFE_HASH_DEFAULT
+#define SHA1DC_INIT_SAFE_HASH_DEFAULT 1
+#endif
 
 #include "sha1.h"
 #include "ubc_check.h"
 
-
-/* 
+#if (defined(__amd64__) || defined(__amd64) || defined(__x86_64__) || defined(__x86_64) || \
+     defined(i386) || defined(__i386) || defined(__i386__) || defined(__i486__)  || \
+     defined(__i586__) || defined(__i686__) || defined(_M_IX86) || defined(__X86__) || \
+     defined(_X86_) || defined(__THW_INTEL__) || defined(__I86__) || defined(__INTEL__) || \
+     defined(__386) || defined(_M_X64) || defined(_M_AMD64))
+#define SHA1DC_ON_INTEL_LIKE_PROCESSOR
+#endif
+
+/*
    Because Little-Endian architectures are most common,
    we only set SHA1DC_BIGENDIAN if one of these conditions is met.
    Note that all MSFT platforms are little endian,
@@ -22,18 +42,93 @@
    If you are compiling on a big endian platform and your compiler does not define one of these,
    you will have to add whatever macros your tool chain defines to indicate Big-Endianness.
  */
-#ifdef SHA1DC_BIGENDIAN
+
+#if defined(__BYTE_ORDER__) && defined(__ORDER_BIG_ENDIAN__)
+/*
+ * Should detect Big Endian under GCC since at least 4.6.0 (gcc svn
+ * rev #165881). See
+ * https://gcc.gnu.org/onlinedocs/cpp/Common-Predefined-Macros.html
+ *
+ * This also works under clang since 3.2, it copied the GCC-ism. See
+ * clang.git's 3b198a97d2 ("Preprocessor: add __BYTE_ORDER__
+ * predefined macro", 2012-07-27)
+ */
+#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
+#define SHA1DC_BIGENDIAN
+#endif
+
+/* Not under GCC-alike */
+#elif defined(__BYTE_ORDER) && defined(__BIG_ENDIAN)
+/*
+ * Should detect Big Endian under glibc.git since 14245eb70e ("entered
+ * into RCS", 1992-11-25). Defined in <endian.h> which will have been
+ * brought in by standard headers. See glibc.git and
+ * https://sourceforge.net/p/predef/wiki/Endianness/
+ */
+#if __BYTE_ORDER == __BIG_ENDIAN
+#define SHA1DC_BIGENDIAN
+#endif
+
+/* Not under GCC-alike or glibc */
+#elif defined(_BYTE_ORDER) && defined(_BIG_ENDIAN) && defined(_LITTLE_ENDIAN)
+/*
+ * *BSD and newlib (embedded linux, cygwin, etc).
+ * the defined(_BIG_ENDIAN) && defined(_LITTLE_ENDIAN) part prevents
+ * this condition from matching with Solaris/sparc.
+ * (Solaris defines only one endian macro)
+ */
+#if _BYTE_ORDER == _BIG_ENDIAN
+#define SHA1DC_BIGENDIAN
+#endif
+
+/* Not under GCC-alike or glibc or *BSD or newlib */
+#elif (defined(__ARMEB__) || defined(__THUMBEB__) || defined(__AARCH64EB__) || \
+       defined(__MIPSEB__) || defined(__MIPSEB) || defined(_MIPSEB) || \
+       defined(__sparc))
+/*
+ * Should define Big Endian for a whitelist of known processors. See
+ * https://sourceforge.net/p/predef/wiki/Endianness/ and
+ * http://www.oracle.com/technetwork/server-storage/solaris/portingtosolaris-138514.html
+ */
+#define SHA1DC_BIGENDIAN
+
+/* Not under GCC-alike or glibc or *BSD or newlib or <processor whitelist> */
+#elif (defined(_AIX) || defined(__hpux))
+
+/*
+ * Defines Big Endian on a whitelist of OSs that are known to be Big
+ * Endian-only. See
+ * https://public-inbox.org/git/93056823-2740-d072-1ebd-46b440b33d7e@felt.demon.nl/
+ */
+#define SHA1DC_BIGENDIAN
+
+/* Not under GCC-alike or glibc or *BSD or newlib or <processor whitelist> or <os whitelist> */
+#elif defined(SHA1DC_ON_INTEL_LIKE_PROCESSOR)
+/*
+ * As a last resort before we do anything else we're not 100% sure
+ * about below, we blacklist specific processors here. We could add
+ * more, see e.g. https://wiki.debian.org/ArchitectureSpecificsMemo
+ */
+#else /* Not under GCC-alike or glibc or *BSD or newlib or <processor whitelist> or <os whitelist> or <processor blacklist> */
+
+/* We do nothing more here for now */
+/*#error "Uncomment this to see if you fall through all the detection"*/
+
+#endif /* Big Endian detection */
+
+#if (defined(SHA1DC_FORCE_LITTLEENDIAN) && defined(SHA1DC_BIGENDIAN))
 #undef SHA1DC_BIGENDIAN
 #endif
-#if (!defined SHA1DC_FORCE_LITTLEENDIAN) && \
-    ((defined(__BYTE_ORDER) && (__BYTE_ORDER == __BIG_ENDIAN)) || \
-    (defined(__BYTE_ORDER__) && (__BYTE_ORDER__ == __BIG_ENDIAN__)) || \
-    defined(__BIG_ENDIAN__) || defined(__ARMEB__) || defined(__THUMBEB__) ||  defined(__AARCH64EB__) || \
-    defined(_MIPSEB) || defined(__MIPSEB) || defined(__MIPSEB__) || defined(SHA1DC_FORCE_BIGENDIAN))
-
+#if (defined(SHA1DC_FORCE_BIGENDIAN) && !defined(SHA1DC_BIGENDIAN))
 #define SHA1DC_BIGENDIAN
-
-#endif /*ENDIANNESS SELECTION*/
+#endif
+/*ENDIANNESS SELECTION*/
+
+#ifndef SHA1DC_FORCE_ALIGNED_ACCESS
+#if defined(SHA1DC_FORCE_UNALIGNED_ACCESS) || defined(SHA1DC_ON_INTEL_LIKE_PROCESSOR)
+#define SHA1DC_ALLOW_UNALIGNED_ACCESS
+#endif /*UNALIGNED ACCESS DETECTION*/
+#endif /*FORCE ALIGNED ACCESS*/
 
 #define rotate_right(x,n) (((x)>>(n))|((x)<<(32-(n))))
 #define rotate_left(x,n)  (((x)<<(n))|((x)>>(32-(n))))
@@ -876,43 +971,48 @@
 	ihvout[0] = ihvin[0] + a; ihvout[1] = ihvin[1] + b; ihvout[2] = ihvin[2] + c; ihvout[3] = ihvin[3] + d; ihvout[4] = ihvin[4] + e; \
 }
 
-#ifdef DOSTORESTATE0
+#ifdef _MSC_VER
+#pragma warning(push)
+#pragma warning(disable: 4127)  /* Compiler complains about the checks in the above macro being constant. */
+#endif
+
+#ifdef DOSTORESTATE00
 SHA1_RECOMPRESS(0)
 #endif
 
-#ifdef DOSTORESTATE1
+#ifdef DOSTORESTATE01
 SHA1_RECOMPRESS(1)
 #endif
 
-#ifdef DOSTORESTATE2
+#ifdef DOSTORESTATE02
 SHA1_RECOMPRESS(2)
 #endif
 
-#ifdef DOSTORESTATE3
+#ifdef DOSTORESTATE03
 SHA1_RECOMPRESS(3)
 #endif
 
-#ifdef DOSTORESTATE4
+#ifdef DOSTORESTATE04
 SHA1_RECOMPRESS(4)
 #endif
 
-#ifdef DOSTORESTATE5
+#ifdef DOSTORESTATE05
 SHA1_RECOMPRESS(5)
 #endif
 
-#ifdef DOSTORESTATE6
+#ifdef DOSTORESTATE06
 SHA1_RECOMPRESS(6)
 #endif
 
-#ifdef DOSTORESTATE7
+#ifdef DOSTORESTATE07
 SHA1_RECOMPRESS(7)
 #endif
 
-#ifdef DOSTORESTATE8
+#ifdef DOSTORESTATE08
 SHA1_RECOMPRESS(8)
 #endif
 
-#ifdef DOSTORESTATE9
+#ifdef DOSTORESTATE09
 SHA1_RECOMPRESS(9)
 #endif
 
@@ -1194,58 +1294,62 @@
 
 #ifdef DOSTORESTATE79
 SHA1_RECOMPRESS(79)
+#endif
+
+#ifdef _MSC_VER
+#pragma warning(pop)
 #endif
 
 static void sha1_recompression_step(uint32_t step, uint32_t ihvin[5], uint32_t ihvout[5], const uint32_t me2[80], const uint32_t state[5])
 {
 	switch (step)
 	{
-#ifdef DOSTORESTATE0
+#ifdef DOSTORESTATE00
 	case 0:
 		sha1recompress_fast_0(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE1
+#ifdef DOSTORESTATE01
 	case 1:
 		sha1recompress_fast_1(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE2
+#ifdef DOSTORESTATE02
 	case 2:
 		sha1recompress_fast_2(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE3
+#ifdef DOSTORESTATE03
 	case 3:
 		sha1recompress_fast_3(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE4
+#ifdef DOSTORESTATE04
 	case 4:
 		sha1recompress_fast_4(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE5
+#ifdef DOSTORESTATE05
 	case 5:
 		sha1recompress_fast_5(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE6
+#ifdef DOSTORESTATE06
 	case 6:
 		sha1recompress_fast_6(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE7
+#ifdef DOSTORESTATE07
 	case 7:
 		sha1recompress_fast_7(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE8
+#ifdef DOSTORESTATE08
 	case 8:
 		sha1recompress_fast_8(ihvin, ihvout, me2, state);
 		break;
 #endif
-#ifdef DOSTORESTATE9
+#ifdef DOSTORESTATE09
 	case 9:
 		sha1recompress_fast_9(ihvin, ihvout, me2, state);
 		break;
@@ -1613,7 +1717,7 @@
 	unsigned i, j;
 	uint32_t ubc_dv_mask[DVMASKSIZE] = { 0xFFFFFFFF };
 	uint32_t ihvtmp[5];
-	
+
 	ctx->ihv1[0] = ctx->ihv[0];
 	ctx->ihv1[1] = ctx->ihv[1];
 	ctx->ihv1[2] = ctx->ihv[2];
@@ -1669,7 +1773,7 @@
 	ctx->ihv[3] = 0x10325476;
 	ctx->ihv[4] = 0xC3D2E1F0;
 	ctx->found_collision = 0;
-	ctx->safe_hash = 1;
+	ctx->safe_hash = SHA1DC_INIT_SAFE_HASH_DEFAULT;
 	ctx->ubc_check = 1;
 	ctx->detect_coll = 1;
 	ctx->reduced_round_coll = 0;
@@ -1717,6 +1821,7 @@
 void SHA1DCUpdate(SHA1_CTX* ctx, const char* buf, size_t len)
 {
 	unsigned left, fill;
+
 	if (len == 0)
 		return;
 
@@ -1735,7 +1840,13 @@
 	while (len >= 64)
 	{
 		ctx->total += 64;
+
+#if defined(SHA1DC_ALLOW_UNALIGNED_ACCESS)
 		sha1_process(ctx, (uint32_t*)(buf));
+#else
+		memcpy(ctx->buffer, buf, 64);
+		sha1_process(ctx, (uint32_t*)(ctx->buffer));
+#endif /* defined(SHA1DC_ALLOW_UNALIGNED_ACCESS) */
 		buf += 64;
 		len -= 64;
 	}
@@ -1794,3 +1905,7 @@
 	output[19] = (unsigned char)(ctx->ihv[4]);
 	return ctx->found_collision;
 }
+
+#ifdef SHA1DC_CUSTOM_TRAILING_INCLUDE_SHA1_C
+#include SHA1DC_CUSTOM_TRAILING_INCLUDE_SHA1_C
+#endif
