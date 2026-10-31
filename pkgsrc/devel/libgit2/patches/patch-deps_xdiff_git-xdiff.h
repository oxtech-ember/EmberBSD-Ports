$NetBSD$

Use the shared Git xdiff source with libgit2 allocator and API policy.

--- deps/xdiff/git-xdiff.h.orig
+++ deps/xdiff/git-xdiff.h
@@ -14,6 +14,8 @@
 #ifndef INCLUDE_git_xdiff_h__
 #define INCLUDE_git_xdiff_h__
 
+#include <limits.h>
+
 #include "regexp.h"
 
 /* Work around C90-conformance issues */
@@ -28,9 +30,28 @@
 #endif
 
 #define XDL_UNUSED GIT_UNUSED_ARG
+#define UNUSED GIT_UNUSED_ARG
+#define XDL_MERGE_ALLOC_EMPTY 0
+#define XDL_REGEX_TYPE git_regexp
+#define XDL_REGMATCH_TYPE git_regmatch
+#define XDF_DIFF_ALGORITHM_MASK (XDF_PATIENCE_DIFF | XDF_HISTOGRAM_DIFF)
+#define XDL_REPORT_BUG(...) git_error_set(GIT_ERROR_INTERNAL, "xdiff invariant violated")
+#define signed_add_overflows(a, b) ((a) > LONG_MAX - (b))
+#define regexec_buf xdl_regexec_buf
 
-#define xdl_malloc(x) git__malloc(x)
-#define xdl_calloc(n, sz) git__calloc(n, sz)
+/* A valid allocator may return NULL for an empty allocation. */
+GIT_INLINE(void *) xdl_malloc_compat(size_t size)
+{
+	return git__malloc(size ? size : 1);
+}
+
+GIT_INLINE(void *) xdl_calloc_compat(size_t count, size_t size)
+{
+	return count && size ? git__calloc(count, size) : git__calloc(1, 1);
+}
+
+#define xdl_malloc(x) xdl_malloc_compat(x)
+#define xdl_calloc(n, sz) xdl_calloc_compat(n, sz)
 #define xdl_free(ptr) git__free(ptr)
 #define xdl_realloc(ptr, x) git__realloc(ptr, x)
 
