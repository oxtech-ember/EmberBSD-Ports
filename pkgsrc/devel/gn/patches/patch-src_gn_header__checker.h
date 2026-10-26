$NetBSD$

Keep the dependency graph comment from splicing the next physical line.
Retain GCC -Werror=comment. No declarations or code change.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- src/gn/header_checker.h.orig
+++ src/gn/header_checker.h
@@ -106,7 +106,7 @@
   //
   // ```
   //     A
-  //    / \
+  //    / \  (edges)
   //   B   C
   //    \ /
   //     D
