# $NetBSD$

Use a correctly typed callback when freeing syntax extensions.

--- src/syntax_extension.h.orig
+++ src/syntax_extension.h
@@ -4,6 +4,10 @@
 #include "cmark-gfm.h"
 #include "cmark-gfm-extension_api.h"
 #include "config.h"
+
+static inline void cmark_syntax_extension_free_cb(cmark_mem *mem, void *extension) {
+  cmark_syntax_extension_free(mem, (cmark_syntax_extension *)extension);
+}
 
 struct cmark_syntax_extension {
   cmark_match_block_func          last_block_matches;
