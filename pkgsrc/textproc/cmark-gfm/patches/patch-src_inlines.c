# $NetBSD$

Preserve desktop-app cmark-gfm hardening changes from upstream fork
3b2bbdc028c1747d1e50d1a32c7f7c61e58c8133,
48a0cf99150a42617762ae67cae65f9a5b88647a and
d7d4a24a9ebfa7581994ea6df0297662bfeaf413.

--- src/inlines.c.orig
+++ src/inlines.c
@@ -675,7 +675,11 @@
   delimiter *opener;
   delimiter *old_closer;
   bool opener_found;
-  bufsize_t openers_bottom[3][128];
+  // Rows are 256 wide because delim_char is an unsigned char that
+  // extensions can set to any value via cmark_inline_parser_push_delimiter;
+  // a 128-wide row would let a high-bit delimiter char index past the
+  // end of this stack array.
+  bufsize_t openers_bottom[3][256];
   int i;
 
   // initialize openers_bottom:
@@ -696,6 +700,11 @@
 
   // now move forward, looking for closers, and handling each
   while (closer != NULL) {
+    // Checkpoint: breaking here leaves the remaining delimiters on the
+    // subject's stack, freed by cmark_parse_inlines' cleanup tail.
+    if (cmark_parser_aborted(parser)) {
+      break;
+    }
     cmark_syntax_extension *extension = get_extension_for_special_char(parser, closer->delim_char);
     if (closer->can_close) {
       // Now look backwards for first matching opener:
@@ -1272,7 +1281,25 @@
       //
       // (first, check for underflows)
       if ((fnref_start_column + 2) <= fnref_end_column) {
-        fnref->as.literal = cmark_chunk_dup(literal, 1, (fnref_end_column - fnref_start_column) - 2);
+        bufsize_t fnref_len = (fnref_end_column - fnref_start_column) - 2;
+        // The label length is derived from source columns, which assumes the
+        // '^' text node's literal points contiguously into the input line.
+        // When that node instead owns its buffer -- e.g. the '^' was produced
+        // by decoding an HTML entity such as `&#94;` -- the buffer holds only
+        // the decoded character and is freed together with the node in the
+        // cleanup loop below. Dup'ing an `fnref_len`-byte non-owning view into
+        // it would read past the allocation and, after the free, read freed
+        // memory (heap use-after-free / out-of-bounds read). Clamp to the
+        // owned length and copy so the reference keeps its own valid buffer.
+        if (literal->alloc) {
+          if (fnref_len > literal->len - 1) {
+            fnref_len = literal->len - 1;
+          }
+          fnref->as.literal = cmark_chunk_dup(literal, 1, fnref_len);
+          cmark_chunk_to_cstr(subj->mem, &fnref->as.literal);
+        } else {
+          fnref->as.literal = cmark_chunk_dup(literal, 1, fnref_len);
+        }
       } else {
         fnref->as.literal = cmark_chunk_dup(literal, 1, 0);
       }
@@ -1539,7 +1566,11 @@
   subject_from_buf(parser->mem, parent->start_line, parent->start_column - 1 + parent->internal_offset, &subj, &content, refmap);
   cmark_chunk_rtrim(&subj.input);
 
-  while (!is_eof(&subj) && parse_inline(parser, &subj, parent, options))
+  // Checkpoint: breaking here falls straight into the cleanup below
+  // (emphasis processing plus the delimiter and bracket stacks), so an
+  // aborted parse frees every subject temporary.
+  while (!is_eof(&subj) && !cmark_parser_aborted(parser) &&
+         parse_inline(parser, &subj, parent, options))
     ;
 
   process_emphasis(parser, &subj, 0);
