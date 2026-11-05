# $NetBSD$

Preserve desktop-app hardening (3b2bbdc, 48a0cf9, d7d4a24).
Make the fork block-quote limit an explicit parser option.

--- src/blocks.c.orig
+++ src/blocks.c
@@ -123,6 +123,8 @@
   cmark_llist *saved_inline_exts = parser->inline_syntax_extensions;
   int saved_options = parser->options;
   cmark_mem *saved_mem = parser->mem;
+  int *saved_abort_flag = parser->allocation_abort_flag;
+  unsigned int saved_max_block_quote_depth = parser->max_block_quote_depth;
 
   cmark_parser_dispose(parser);
 
@@ -141,6 +143,8 @@
   parser->syntax_extensions = saved_exts;
   parser->inline_syntax_extensions = saved_inline_exts;
   parser->options = saved_options;
+  parser->allocation_abort_flag = saved_abort_flag;
+  parser->max_block_quote_depth = saved_max_block_quote_depth;
 }
 
 cmark_parser *cmark_parser_new_with_mem(int options, cmark_mem *mem) {
@@ -156,7 +160,22 @@
   return cmark_parser_new_with_mem(options, &CMARK_DEFAULT_MEM_ALLOCATOR);
 }
 
+void cmark_parser_set_allocation_abort_flag(cmark_parser *parser,
+                                            int *abort_flag) {
+  if (parser == NULL)
+    return;
+  parser->allocation_abort_flag = abort_flag;
+}
+
+void cmark_parser_set_max_block_quote_depth(cmark_parser *parser,
+                                             unsigned int max_depth) {
+  if (parser != NULL)
+    parser->max_block_quote_depth = max_depth;
+}
+
 void cmark_parser_free(cmark_parser *parser) {
+  if (parser == NULL)
+    return;
   cmark_mem *mem = parser->mem;
   cmark_parser_dispose(parser);
   cmark_strbuf_free(&parser->curline);
@@ -248,18 +267,23 @@
 }
 
 // Check to see if a node ends with a blank line, descending
-// if needed into lists and sublists.
+// if needed into lists and sublists. The descent is iterative:
+// nested lists can be tens of thousands of levels deep (lists match
+// across lines while the per-line MAX_LIST_DEPTH counter resets), and
+// a recursive descent overflows the stack in builds that don't turn
+// the tail call into a jump.
 static bool S_ends_with_blank_line(cmark_node *node) {
-  if (S_last_line_checked(node)) {
-    return(S_last_line_blank(node));
-  } else if ((S_type(node) == CMARK_NODE_LIST ||
-              S_type(node) == CMARK_NODE_ITEM) && node->last_child) {
-    S_set_last_line_checked(node);
-    return(S_ends_with_blank_line(node->last_child));
-  } else {
-    S_set_last_line_checked(node);
-    return (S_last_line_blank(node));
-  }
+  while (!S_last_line_checked(node)) {
+    if ((S_type(node) == CMARK_NODE_LIST || S_type(node) == CMARK_NODE_ITEM) &&
+        node->last_child) {
+      S_set_last_line_checked(node);
+      node = node->last_child;
+    } else {
+      S_set_last_line_checked(node);
+      break;
+    }
+  }
+  return S_last_line_blank(node);
 }
 
 // returns true if content remains after link defs are resolved.
@@ -444,6 +468,11 @@
 
   while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
     cur = cmark_iter_get_node(iter);
+    // Checkpoint: blocks parsed so far stay complete and owned by the
+    // tree; the remaining ones are never touched.
+    if (cmark_parser_aborted(parser)) {
+      break;
+    }
     if (ev_type == CMARK_EVENT_ENTER) {
       if (contains_inlines(cur)) {
         cmark_parse_inlines(parser, cur, refmap, options);
@@ -476,6 +505,10 @@
 
   while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
     cur = cmark_iter_get_node(iter);
+    // Checkpoint: stopping here keeps every map entry owned by the map.
+    if (cmark_parser_aborted(parser)) {
+      break;
+    }
     if (ev_type == CMARK_EVENT_EXIT && cur->type == CMARK_NODE_FOOTNOTE_DEFINITION) {
       cmark_footnote_create(map, cur);
     }
@@ -487,6 +520,11 @@
 
   while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
     cur = cmark_iter_get_node(iter);
+    // Checkpoint: stopping here leaves the node surgery below either
+    // fully done or not started for the current node.
+    if (cmark_parser_aborted(parser)) {
+      break;
+    }
     if (ev_type == CMARK_EVENT_EXIT && cur->type == CMARK_NODE_FOOTNOTE_REFERENCE) {
       cmark_footnote *footnote = (cmark_footnote *)cmark_map_lookup(map, &cur->as.literal);
       if (footnote) {
@@ -720,7 +758,14 @@
   else
     parser->total_size += len;
 
-  if (parser->last_buffer_ended_with_cr && *buffer == '\n') {
+  if (len == 0 && !eof) {
+    // A zero-length non-final feed is a no-op: the buffer pointer may be
+    // invalid, and clearing last_buffer_ended_with_cr here would corrupt
+    // a CR/LF line ending split across two feeds.
+    return;
+  }
+
+  if (parser->last_buffer_ended_with_cr && len > 0 && *buffer == '\n') {
     // skip NL if last buffer ended with CR ; see #117
     buffer++;
   }
@@ -729,6 +774,12 @@
     const unsigned char *eol;
     bufsize_t chunk_len;
     bool process = false;
+
+    // Checkpoint: stopping between lines leaves every parser temporary
+    // owned by the parser or the partial tree.
+    if (cmark_parser_aborted(parser)) {
+      return;
+    }
     for (eol = buffer; eol < end; ++eol) {
       if (S_is_line_end_char(*eol)) {
         process = true;
@@ -742,7 +793,13 @@
       process = true;
     }
 
-    chunk_len = (bufsize_t)(eol - buffer);
+    // A single line longer than what bufsize_t can address would wrap
+    // chunk_len negative and move the buffer pointer backwards; clamp the
+    // chunk and let the strbuf size limit in cmark_strbuf_grow handle the
+    // oversized input instead.
+    chunk_len = ((uintmax_t)(eol - buffer) > (uintmax_t)INT32_MAX)
+                    ? INT32_MAX
+                    : (bufsize_t)(eol - buffer);
     if (process) {
       if (parser->linebuf.size > 0) {
         cmark_strbuf_put(&parser->linebuf, buffer, chunk_len);
@@ -1135,7 +1192,9 @@
     S_find_first_nonspace(parser, input);
     indented = parser->indent >= CODE_INDENT;
 
-    if (!indented && peek_at(input, parser->first_nonspace) == '>') {
+    if (!indented && (!parser->max_block_quote_depth ||
+        (unsigned int)depth < parser->max_block_quote_depth) &&
+        peek_at(input, parser->first_nonspace) == '>') {
 
       bufsize_t blockquote_startpos = parser->first_nonspace;
 
@@ -1525,6 +1584,10 @@
   if (parser->root == NULL)
     return NULL;
 
+  if (cmark_parser_aborted(parser)) {
+    goto aborted;
+  }
+
   if (parser->linebuf.size) {
     S_process_line(parser, parser->linebuf.ptr, parser->linebuf.size);
     cmark_strbuf_clear(&parser->linebuf);
@@ -1542,6 +1605,10 @@
     abort();
   }
 #endif
+
+  if (cmark_parser_aborted(parser)) {
+    goto aborted;
+  }
 
   for (extensions = parser->syntax_extensions; extensions; extensions = extensions->next) {
     cmark_syntax_extension *ext = (cmark_syntax_extension *) extensions->data;
@@ -1550,6 +1617,10 @@
       if (processed)
         parser->root = processed;
     }
+    // Checkpoint: stop before postprocessing more extensions.
+    if (cmark_parser_aborted(parser)) {
+      break;
+    }
   }
 
   res = parser->root;
@@ -1557,7 +1628,26 @@
 
   cmark_parser_reset(parser);
 
+  if (cmark_parser_aborted(parser)) {
+    // The abort may have tripped during postprocessing after the tree
+    // was detached from the parser.
+    cmark_node_free(res);
+    return NULL;
+  }
+
   return res;
+
+aborted:
+  // Everything allocated belongs either to the parser or to the partial
+  // tree, and every in-flight subject has run its cleanup tail, so the
+  // normal dispose paths release it all. cmark_parser_reset() disposes
+  // the still-attached partial tree and refmap exactly once; the strbuf
+  // frees mirror the normal path because reset reinitializes without
+  // freeing.
+  cmark_strbuf_free(&parser->curline);
+  cmark_strbuf_free(&parser->linebuf);
+  cmark_parser_reset(parser);
+  return NULL;
 }
 
 int cmark_parser_get_line_number(cmark_parser *parser) {
