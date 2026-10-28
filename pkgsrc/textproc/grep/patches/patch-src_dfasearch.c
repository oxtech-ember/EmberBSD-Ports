$NetBSD$

Preserve the existing bitwise condition while making its precedence explicit
for Clang. Origin: EmberBSD (AI-assisted); not yet submitted upstream.

--- src/dfasearch.c.orig
+++ src/dfasearch.c
@@ -149,7 +149,7 @@
   /* Do not use a fastmap with -i, to work around glibc Bug#20381.  */
   static_assert (UCHAR_MAX < IDX_MAX);
   idx_t uchar_max = UCHAR_MAX;
-  pat.fastmap = syntax_only | match_icase ? nullptr : ximalloc (uchar_max + 1);
+  pat.fastmap = (syntax_only | match_icase) ? nullptr : ximalloc (uchar_max + 1);
 
   pat.translate = nullptr;
 
