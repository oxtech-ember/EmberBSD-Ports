# $NetBSD$

Use a correctly typed callback when freeing syntax extensions.
Preserve the desktop-app null-name guard from commit d7d4a24.

--- src/registry.c.orig
+++ src/registry.c
@@ -36,7 +36,7 @@
     cmark_llist_free_full(
         &CMARK_DEFAULT_MEM_ALLOCATOR,
         syntax_extensions,
-        (cmark_free_func) cmark_syntax_extension_free);
+        cmark_syntax_extension_free_cb);
     syntax_extensions = NULL;
   }
 }
@@ -54,6 +54,9 @@
 cmark_syntax_extension *cmark_find_syntax_extension(const char *name) {
   cmark_llist *tmp;
 
+  if (name == NULL)
+    return NULL;
+
   for (tmp = syntax_extensions; tmp; tmp = tmp->next) {
     cmark_syntax_extension *ext = (cmark_syntax_extension *) tmp->data;
     if (!strcmp(ext->name, name))
