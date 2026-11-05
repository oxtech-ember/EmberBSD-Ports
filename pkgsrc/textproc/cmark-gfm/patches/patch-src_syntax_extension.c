# $NetBSD$

Preserve desktop-app cmark-gfm hardening changes from upstream fork
3b2bbdc028c1747d1e50d1a32c7f7c61e58c8133,
48a0cf99150a42617762ae67cae65f9a5b88647a and
d7d4a24a9ebfa7581994ea6df0297662bfeaf413.

--- src/syntax_extension.c.orig
+++ src/syntax_extension.c
@@ -10,6 +10,9 @@
 static cmark_mem *_mem = &CMARK_DEFAULT_MEM_ALLOCATOR;
 
 void cmark_syntax_extension_free(cmark_mem *mem, cmark_syntax_extension *extension) {
+  if (extension == NULL)
+    return;
+
   if (extension->free_function && extension->priv) {
     extension->free_function(mem, extension->priv);
   }
@@ -20,7 +23,12 @@
 }
 
 cmark_syntax_extension *cmark_syntax_extension_new(const char *name) {
-  cmark_syntax_extension *res = (cmark_syntax_extension *) _mem->calloc(1, sizeof(cmark_syntax_extension));
+  cmark_syntax_extension *res = NULL;
+
+  if (name == NULL)
+    return NULL;
+
+  res = (cmark_syntax_extension *) _mem->calloc(1, sizeof(cmark_syntax_extension));
   res->name = (char *) _mem->calloc(1, sizeof(char) * (strlen(name)) + 1);
   strcpy(res->name, name);
   return res;
