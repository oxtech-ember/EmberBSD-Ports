# $NetBSD$

Preserve desktop-app cmark-gfm hardening changes from upstream fork
3b2bbdc028c1747d1e50d1a32c7f7c61e58c8133,
48a0cf99150a42617762ae67cae65f9a5b88647a and
d7d4a24a9ebfa7581994ea6df0297662bfeaf413.

--- src/iterator.c.orig
+++ src/iterator.c
@@ -21,7 +21,12 @@
   return iter;
 }
 
-void cmark_iter_free(cmark_iter *iter) { iter->mem->free(iter); }
+void cmark_iter_free(cmark_iter *iter) {
+  if (iter == NULL) {
+    return;
+  }
+  iter->mem->free(iter);
+}
 
 static bool S_is_leaf(cmark_node *node) {
   switch (node->type) {
@@ -39,6 +44,9 @@
 }
 
 cmark_event_type cmark_iter_next(cmark_iter *iter) {
+  if (iter == NULL) {
+    return CMARK_EVENT_DONE;
+  }
   cmark_event_type ev_type = iter->next.ev_type;
   cmark_node *node = iter->next.node;
 
@@ -79,18 +87,25 @@
 
 void cmark_iter_reset(cmark_iter *iter, cmark_node *current,
                       cmark_event_type event_type) {
+  if (iter == NULL || current == NULL) {
+    return;
+  }
   iter->next.ev_type = event_type;
   iter->next.node = current;
   cmark_iter_next(iter);
 }
 
-cmark_node *cmark_iter_get_node(cmark_iter *iter) { return iter->cur.node; }
+cmark_node *cmark_iter_get_node(cmark_iter *iter) {
+  return iter ? iter->cur.node : NULL;
+}
 
 cmark_event_type cmark_iter_get_event_type(cmark_iter *iter) {
-  return iter->cur.ev_type;
+  return iter ? iter->cur.ev_type : CMARK_EVENT_NONE;
 }
 
-cmark_node *cmark_iter_get_root(cmark_iter *iter) { return iter->root; }
+cmark_node *cmark_iter_get_root(cmark_iter *iter) {
+  return iter ? iter->root : NULL;
+}
 
 void cmark_consolidate_text_nodes(cmark_node *root) {
   if (root == NULL) {
