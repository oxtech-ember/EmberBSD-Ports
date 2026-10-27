Origin: EmberBSD; narrow unused-function fix for swap32 in tests/util/pattern.c.
Status: local; replaces package-wide -Wno-error=unused-function under Clang.

--- tests/util/pattern.c.orig
+++ tests/util/pattern.c
@@ -76,7 +76,8 @@
 	return ((x & 0x00ffU) << 8) | ((x & 0xff00U) >> 8);
 }
 
-static inline uint32_t swap32(uint32_t x)
+/* Unused on little-endian when cairo tests are disabled (no byteswap path). */
+static inline uint32_t __attribute__((unused)) swap32(uint32_t x)
 {
 	return ((x & 0x000000ffU) << 24) |
 	       ((x & 0x0000ff00U) <<  8) |
