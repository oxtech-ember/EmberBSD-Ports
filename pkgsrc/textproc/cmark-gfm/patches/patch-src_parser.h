# $NetBSD$

Preserve desktop-app hardening (3b2bbdc, 48a0cf9, d7d4a24).
Make the fork block-quote limit an explicit parser option.

--- src/parser.h.orig
+++ src/parser.h
@@ -50,7 +50,19 @@
   cmark_llist *syntax_extensions;
   cmark_llist *inline_syntax_extensions;
   cmark_ispunct_func backslash_ispunct;
+  /* Fork addition: optional host-owned abort flag, see
+   * cmark_parser_set_allocation_abort_flag() in cmark-gfm.h. */
+  int *allocation_abort_flag;
+  unsigned int max_block_quote_depth;
 };
+
+/* Fork addition: polls the host-owned abort flag. The parser checks
+ * this only at points where stopping early leaves every temporary on
+ * its normal cleanup path, so an aborted parse frees everything it
+ * allocated. */
+static CMARK_INLINE int cmark_parser_aborted(cmark_parser *parser) {
+  return parser->allocation_abort_flag && *parser->allocation_abort_flag;
+}
 
 #ifdef __cplusplus
 }
