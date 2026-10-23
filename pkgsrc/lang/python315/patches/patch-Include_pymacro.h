$NetBSD: patch-Include_pymacro.h,v 1.1 2026/10/10 10:34:19 adam Exp $

Fix build on NetBSD: error: initializer element is not constant.
Keep the C11 assertion an integer constant expression on GCC16 hosts.
Origin: EmberBSD (AI-assisted), preserve the compile-time assertion.

--- Include/pymacro.h.orig	2025-02-04 14:51:09.000000000 +0000
+++ Include/pymacro.h
@@ -138,10 +138,9 @@
 #define Py_CHARMASK(c) ((unsigned char)((c) & 0xff))
 
 #if (defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L \
-     && !defined(__cplusplus) && !defined(_MSC_VER))
+     && !defined(__cplusplus) && !defined(_MSC_VER) && !defined(__NetBSD__) && !defined(__sun))
 #  define Py_BUILD_ASSERT_EXPR(cond) \
-    ((void)sizeof(struct { int dummy; _Static_assert(cond, #cond); }), \
-     0)
+    (0 * (int)sizeof(struct { int dummy; _Static_assert(cond, #cond); }))
 #else
    /* Assert a build-time dependency, as an expression.
     *
