# $NetBSD$

Preserve desktop-app cmark-gfm hardening changes from upstream fork
3b2bbdc028c1747d1e50d1a32c7f7c61e58c8133,
48a0cf99150a42617762ae67cae65f9a5b88647a and
d7d4a24a9ebfa7581994ea6df0297662bfeaf413.

--- src/node.c.orig
+++ src/node.c
@@ -42,7 +42,7 @@
 void cmark_init_standard_node_flags(void) {}
 
 bool cmark_node_can_contain_type(cmark_node *node, cmark_node_type child_type) {
-  if (child_type == CMARK_NODE_DOCUMENT) {
+  if (node == NULL || child_type == CMARK_NODE_DOCUMENT) {
       return false;
     }
 
@@ -200,6 +200,9 @@
 }
 
 void cmark_node_free(cmark_node *node) {
+  if (node == NULL) {
+    return;
+  }
   S_node_unlink(node);
   node->next = NULL;
   S_free_nodes(node);
@@ -215,6 +218,9 @@
 
 int cmark_node_set_type(cmark_node * node, cmark_node_type type) {
   cmark_node_type initial_type;
+
+  if (node == NULL)
+    return 0;
 
   if (type == node->type)
     return 1;
@@ -416,10 +422,16 @@
 }
 
 const char *cmark_node_get_string_content(cmark_node *node) {
+  if (node == NULL) {
+    return NULL;
+  }
   return (char *) node->content.ptr;
 }
 
 int cmark_node_set_string_content(cmark_node *node, const char *content) {
+  if (node == NULL) {
+    return false;
+  }
   cmark_strbuf_sets(&node->content, content);
   return true;
 }
@@ -850,6 +862,9 @@
 }
 
 void cmark_node_unlink(cmark_node *node) {
+  if (node == NULL) {
+    return;
+  }
   S_node_unlink(node);
 
   node->next = NULL;
@@ -858,7 +873,7 @@
 }
 
 int cmark_node_insert_before(cmark_node *node, cmark_node *sibling) {
-  if (node == NULL || sibling == NULL) {
+  if (node == NULL || sibling == NULL || node == sibling) {
     return 0;
   }
 
@@ -891,7 +906,7 @@
 }
 
 int cmark_node_insert_after(cmark_node *node, cmark_node *sibling) {
-  if (node == NULL || sibling == NULL) {
+  if (node == NULL || sibling == NULL || node == sibling) {
     return 0;
   }
 
@@ -924,6 +939,12 @@
 }
 
 int cmark_node_replace(cmark_node *oldnode, cmark_node *newnode) {
+  if (oldnode == NULL || newnode == NULL) {
+    return 0;
+  }
+  if (oldnode == newnode) {
+    return 1;
+  }
   if (!cmark_node_insert_before(oldnode, newnode)) {
     return 0;
   }
@@ -932,7 +953,9 @@
 }
 
 int cmark_node_prepend_child(cmark_node *node, cmark_node *child) {
-  if (!S_can_contain(node, child)) {
+  // Ancestor-cycle checks stay gated behind enable_safety_checks: they cost
+  // O(depth) per call, which is input-reachable through nested structures.
+  if (node == child || !S_can_contain(node, child)) {
     return 0;
   }
 
@@ -956,7 +979,7 @@
 }
 
 int cmark_node_append_child(cmark_node *node, cmark_node *child) {
-  if (!S_can_contain(node, child)) {
+  if (node == child || !S_can_contain(node, child)) {
     return 0;
   }
 
