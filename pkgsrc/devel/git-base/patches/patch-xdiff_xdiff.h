$NetBSD$

Allow source consumers to supply compatible allocation and policy hooks;
keep the Git defaults unchanged. Origin: EmberBSD contributors (AI-assisted).

--- xdiff/xdiff.h.orig
+++ xdiff/xdiff.h
@@ -27,6 +27,13 @@
 extern "C" {
 #endif /* #ifdef __cplusplus */
 
+#ifndef XDL_REGEX_TYPE
+#define XDL_REGEX_TYPE regex_t
+#endif
+#ifndef XDL_REGMATCH_TYPE
+#define XDL_REGMATCH_TYPE regmatch_t
+#endif
+
 /* xpparm_t.flags */
 #define XDF_NEED_MINIMAL (1 << 0)
 
@@ -43,7 +50,9 @@
 
 #define XDF_PATIENCE_DIFF (1 << 14)
 #define XDF_HISTOGRAM_DIFF (1 << 15)
+#ifndef XDF_DIFF_ALGORITHM_MASK
 #define XDF_DIFF_ALGORITHM_MASK (XDF_PATIENCE_DIFF | XDF_HISTOGRAM_DIFF | XDF_NEED_MINIMAL)
+#endif
 #define XDF_DIFF_ALG(x) ((x) & XDF_DIFF_ALGORITHM_MASK)
 
 #define XDF_INDENT_HEURISTIC (1 << 23)
@@ -82,7 +91,7 @@
 	unsigned long flags;
 
 	/* -I<regex> */
-	regex_t **ignore_regex;
+	XDL_REGEX_TYPE **ignore_regex;
 	size_t ignore_regex_nr;
 
 	/* See Documentation/diff-options.adoc. */
@@ -119,10 +128,18 @@
 } bdiffparam_t;
 
 
+#ifndef xdl_malloc
 #define xdl_malloc(x) xmalloc(x)
+#endif
+#ifndef xdl_calloc
 #define xdl_calloc(n, sz) xcalloc(n, sz)
+#endif
+#ifndef xdl_free
 #define xdl_free(ptr) free(ptr)
+#endif
+#ifndef xdl_realloc
 #define xdl_realloc(ptr,x) xrealloc(ptr,x)
+#endif
 
 void *xdl_mmfile_first(mmfile_t *mmf, long *size);
 long xdl_mmfile_size(mmfile_t *mmf);
