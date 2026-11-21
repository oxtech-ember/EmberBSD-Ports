$NetBSD$

Adapt token-boundary and clone accounting from Telegram twidget in tdesktop v7.4.4
(Telegram/ThirdParty/twidget/litehtml/src/gumbo/parser.c, Apache-2.0).
Preserve unbounded callers and cover the current selectedcontent clone path.

--- src/parser.c.orig
+++ src/parser.c
@@ -18,6 +18,7 @@
 #include <ctype.h>
 #include <stdarg.h>
 #include <stdlib.h>
+#include <stdint.h>
 #include <string.h>
 #include <strings.h>
 
@@ -440,6 +441,8 @@
   // flag appropriately.
   bool _closed_body_tag;
   bool _closed_html_tag;
+  const GumboLimits* _limits;
+  size_t _remaining_clone_bytes;
 } GumboParserState;
 
 static bool token_has_attribute(const GumboToken* token, const char* name) {
@@ -511,6 +514,7 @@
 static void output_init(GumboParser* parser) {
   GumboOutput* output = gumbo_parser_allocate(parser, sizeof(GumboOutput));
   output->root = NULL;
+  output->truncated = false;
   output->document = new_document_node(parser);
   parser->_output = output;
   gumbo_init_errors(parser);
@@ -537,6 +541,8 @@
   parser_state->_current_token = NULL;
   parser_state->_closed_body_tag = false;
   parser_state->_closed_html_tag = false;
+  parser_state->_limits = NULL;
+  parser_state->_remaining_clone_bytes = 0;
   parser->_parser_state = parser_state;
 }
 
@@ -985,6 +991,21 @@
                                   : kGumboEmptyString;
 }
 
+// Charge the node plus its source span without overflowing size_t.
+static void account_clone(GumboParser* parser, const GumboNode* node,
+    size_t source_length) {
+  GumboParserState* state = parser->_parser_state;
+  if (!state->_limits || parser->_output->truncated) {
+    return;
+  }
+  if (state->_remaining_clone_bytes < sizeof(*node) ||
+      source_length > state->_remaining_clone_bytes - sizeof(*node)) {
+    parser->_output->truncated = true;
+  } else {
+    state->_remaining_clone_bytes -= sizeof(*node) + source_length;
+  }
+}
+
 static GumboNode* clone_node_recursively(GumboParser* parser, const GumboNode* src) {
   if (!src) {
     return NULL;
@@ -996,6 +1017,10 @@
     case GUMBO_NODE_WHITESPACE:
     case GUMBO_NODE_COMMENT:
     case GUMBO_NODE_PROCESSING_INSTRUCTION: {
+      account_clone(parser, src, src->v.text.original_text.length);
+      if (parser->_output->truncated) {
+        return NULL;
+      }
       GumboNode* t = create_node(parser, src->type);
       const char* s = src->v.text.text;
       t->v.text.text = s ? gumbo_copy_stringz(parser, s) : NULL;
@@ -1007,6 +1032,10 @@
 
     case GUMBO_NODE_ELEMENT:
     case GUMBO_NODE_TEMPLATE: {
+      account_clone(parser, src, src->v.element.original_tag.length);
+      if (parser->_output->truncated) {
+        return NULL;
+      }
       GumboNode* e = create_node(parser, src->type);
       GumboElement* dst = &e->v.element;
       const GumboElement* se = &src->v.element;
@@ -1460,6 +1489,7 @@
 GumboNode* clone_node(
     GumboParser* parser, GumboNode* node, GumboParseFlags reason) {
   assert(node->type == GUMBO_NODE_ELEMENT || node->type == GUMBO_NODE_TEMPLATE);
+  account_clone(parser, node, node->v.element.original_tag.length);
   GumboNode* new_node = gumbo_parser_allocate(parser, sizeof(GumboNode));
   *new_node = *node;
   new_node->parent = NULL;
@@ -4420,11 +4450,22 @@
 
 GumboOutput* gumbo_parse_with_options(
     const GumboOptions* options, const char* buffer, size_t length) {
+  return gumbo_parse_with_limits(options, buffer, length, NULL);
+}
+
+GumboOutput* gumbo_parse_with_limits(const GumboOptions* options,
+    const char* buffer, size_t length, const GumboLimits* limits) {
   GumboParser parser;
   parser._options = options;
   output_init(&parser);
   gumbo_tokenizer_state_init(&parser, buffer, length);
   parser_state_init(&parser);
+  if (limits) {
+    parser._parser_state->_limits = limits;
+    parser._parser_state->_remaining_clone_bytes =
+        limits->max_extra_clone_bytes > SIZE_MAX - length ? SIZE_MAX :
+        length + limits->max_extra_clone_bytes;
+  }
 
   if (options->fragment_context != GUMBO_TAG_LAST) {
     fragment_parser_init(
@@ -4445,6 +4486,14 @@
     if (state->_reprocess_current_token) {
       state->_reprocess_current_token = false;
     } else {
+      // Finish the current token and any buffered text before finalizing the
+      // partial document. The same cleanup path handles a normal end of input.
+      if (limits && state->_text_node._buffer.length == 0 &&
+          (parser._output->truncated ||
+           state->_open_elements.length > limits->max_open_elements)) {
+        parser._output->truncated = true;
+        break;
+      }
       GumboNode* current_node = get_current_node(&parser);
       gumbo_tokenizer_set_is_current_node_foreign(&parser,
           current_node &&
