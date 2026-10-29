$NetBSD$

Backport platform SIMD selection from libjpeg-turbo 3.2.1 while retaining libspng gamma support.

Origin: libjpeg-turbo contributors; EmberBSD (AI-assisted).

--- spng/spng.c.orig
+++ spng/spng.c
@@ -35,14 +35,16 @@
 
 #ifndef SPNG_DISABLE_OPT
 
-    #if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
+    #if (defined(__i386__) && defined(__SSE2__)) || defined(__x86_64__) || \
+        (defined(_M_IX86) && defined(_M_IX86_FP) && _M_IX86_FP >= 2) || \
+        (defined(_M_X64) && !defined(_M_ARM64EC))
         #define SPNG_X86
 
         #if defined(__x86_64__) || defined(_M_X64)
             #define SPNG_X86_64
         #endif
 
-    #elif defined(__aarch64__) || defined(_M_ARM64) /* || defined(__ARM_NEON) */
+    #elif defined(__aarch64__) || defined(_M_ARM64) || defined(_M_ARM64EC) /* || defined(__ARM_NEON) */
         #define SPNG_ARM /* NOTE: only arm64 builds are tested! */
     #else
         #pragma message "disabling SIMD optimizations for unknown target"
@@ -6603,7 +6605,7 @@
    (temp_pointer = png_ptr(type,pointer), *temp_pointer)
 
 
-#if defined(_MSC_VER) && !defined(__clang__) && defined(_M_ARM64)
+#if defined(_MSC_VER) && !defined(__clang__) && (defined(_M_ARM64) || defined(_M_ARM64EC))
     #include <arm64_neon.h>
 #else
     #include <arm_neon.h>
