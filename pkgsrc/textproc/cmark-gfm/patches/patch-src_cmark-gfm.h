# $NetBSD$

Preserve desktop-app hardening (3b2bbdc, 48a0cf9, d7d4a24).
Make the fork block-quote limit an explicit parser option.

--- src/cmark-gfm.h.orig
+++ src/cmark-gfm.h
@@ -578,6 +578,30 @@
  */
 CMARK_GFM_EXPORT
 cmark_parser *cmark_parser_new_with_mem(int options, cmark_mem *mem);
+
+/** Fork addition: sets a host-owned abort flag the parser polls while
+ * parsing. A host that bounds parse memory through a custom cmark_mem
+ * raises this flag when its budget is exhausted; the parser then stops
+ * at its next checkpoint, chosen so that everything allocated so far is
+ * still released through normal cleanup paths. cmark_parser_finish()
+ * frees the partial tree and returns NULL for such a parse.
+ * The pointed-to int must remain valid until replaced with NULL or until
+ * parser destruction; the pointer persists across parser reset. Passing
+ * NULL removes it. Do not modify the int concurrently without synchronization.
+ */
+CMARK_GFM_EXPORT
+void cmark_parser_set_allocation_abort_flag(cmark_parser *parser,
+                                            int *abort_flag);
+
+/** Set an exclusive per-line threshold on new container-opening iterations
+ * for recognizing block quotes. The count includes other new containers;
+ * e.g. threshold 512 permits 511 consecutive new quotes on an empty line.
+ * Zero (the default) preserves unlimited behavior. The setting persists
+ * across parser reset.
+ */
+CMARK_GFM_EXPORT
+void cmark_parser_set_max_block_quote_depth(cmark_parser *parser,
+                                             unsigned int max_depth);
 
 /** Frees memory allocated for a parser object.
  */
