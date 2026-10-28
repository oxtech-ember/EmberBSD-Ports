$NetBSD$

Preserve pkgsrc Chromium's OpenBSD SVE exclusion with V8 15.6's shared guard.
Origin: NetBSD pkgsrc Chromium patch-v8_src_objects_simd.cc, based on OpenBSD
Chromium patches and pkgsrc qt5-qtwebengine patches; adapted by EmberBSD.

--- src/objects/simd.cc.orig
+++ src/objects/simd.cc
@@ -353,6 +353,7 @@
 // mangling SVE types with the Microsoft C++ ABI since version 21.
 // Fallback to Neon in cases where SVE is not supported.
 #if defined(NEON64) && defined(__clang__) && \
+    !defined(V8_TARGET_OS_OPENBSD) && \
     (!defined(V8_TARGET_OS_WIN) || __clang_major__ >= 21)
 #define V8_ENABLE_SIMD_SVE 1
 
