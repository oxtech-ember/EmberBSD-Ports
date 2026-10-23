$NetBSD$

Express the byte alignment of optimized unaligned-access aliases for GCC and
Clang. This keeps the selected LZO fast path while allowing UBSan to model the
unaligned accesses supported by the target architecture. Packaging is
AI-assisted.

--- src/lzo_func.h.orig
+++ src/lzo_func.h
@@ -177,6 +177,11 @@
 #ifndef lzo_memops_TU2p
 #if (LZO_OPT_UNALIGNED16)
+#if (LZO_CC_GNUC >= 0x030400ul) || (LZO_CC_CLANG >= 0x020900ul)
+typedef lzo_uint16_t __lzo_may_alias
+    __attribute__((__aligned__(1))) lzo_memops_TU2;
+#else
 typedef lzo_uint16_t __lzo_may_alias lzo_memops_TU2;
+#endif
 #define lzo_memops_TU2p volatile lzo_memops_TU2 *
 #elif defined(__lzo_byte_struct)
 __lzo_byte_struct(lzo_memops_TU2_struct,2)
@@ -192,6 +197,11 @@
 #ifndef lzo_memops_TU4p
 #if (LZO_OPT_UNALIGNED32)
+#if (LZO_CC_GNUC >= 0x030400ul) || (LZO_CC_CLANG >= 0x020900ul)
+typedef lzo_uint32_t __lzo_may_alias
+    __attribute__((__aligned__(1))) lzo_memops_TU4;
+#else
 typedef lzo_uint32_t __lzo_may_alias lzo_memops_TU4;
+#endif
 #define lzo_memops_TU4p volatile lzo_memops_TU4 __LZO_MMODEL *
 #elif defined(__lzo_byte_struct)
 __lzo_byte_struct(lzo_memops_TU4_struct,4)
@@ -207,6 +217,11 @@
 #ifndef lzo_memops_TU8p
 #if (LZO_OPT_UNALIGNED64)
+#if (LZO_CC_GNUC >= 0x030400ul) || (LZO_CC_CLANG >= 0x020900ul)
+typedef lzo_uint64_t __lzo_may_alias
+    __attribute__((__aligned__(1))) lzo_memops_TU8;
+#else
 typedef lzo_uint64_t __lzo_may_alias lzo_memops_TU8;
+#endif
 #define lzo_memops_TU8p volatile lzo_memops_TU8 __LZO_MMODEL *
 #elif defined(__lzo_byte_struct)
 __lzo_byte_struct(lzo_memops_TU8_struct,8)
--- minilzo/minilzo.c.orig
+++ minilzo/minilzo.c
@@ -3675,6 +3675,11 @@
 #ifndef lzo_memops_TU2p
 #if (LZO_OPT_UNALIGNED16)
+#if (LZO_CC_GNUC >= 0x030400ul) || (LZO_CC_CLANG >= 0x020900ul)
+typedef lzo_uint16_t __lzo_may_alias
+    __attribute__((__aligned__(1))) lzo_memops_TU2;
+#else
 typedef lzo_uint16_t __lzo_may_alias lzo_memops_TU2;
+#endif
 #define lzo_memops_TU2p volatile lzo_memops_TU2 *
 #elif defined(__lzo_byte_struct)
 __lzo_byte_struct(lzo_memops_TU2_struct,2)
@@ -3690,6 +3695,11 @@
 #ifndef lzo_memops_TU4p
 #if (LZO_OPT_UNALIGNED32)
+#if (LZO_CC_GNUC >= 0x030400ul) || (LZO_CC_CLANG >= 0x020900ul)
+typedef lzo_uint32_t __lzo_may_alias
+    __attribute__((__aligned__(1))) lzo_memops_TU4;
+#else
 typedef lzo_uint32_t __lzo_may_alias lzo_memops_TU4;
+#endif
 #define lzo_memops_TU4p volatile lzo_memops_TU4 __LZO_MMODEL *
 #elif defined(__lzo_byte_struct)
 __lzo_byte_struct(lzo_memops_TU4_struct,4)
@@ -3705,6 +3715,11 @@
 #ifndef lzo_memops_TU8p
 #if (LZO_OPT_UNALIGNED64)
+#if (LZO_CC_GNUC >= 0x030400ul) || (LZO_CC_CLANG >= 0x020900ul)
+typedef lzo_uint64_t __lzo_may_alias
+    __attribute__((__aligned__(1))) lzo_memops_TU8;
+#else
 typedef lzo_uint64_t __lzo_may_alias lzo_memops_TU8;
+#endif
 #define lzo_memops_TU8p volatile lzo_memops_TU8 __LZO_MMODEL *
 #elif defined(__lzo_byte_struct)
 __lzo_byte_struct(lzo_memops_TU8_struct,8)
