# $NetBSD$

Use a correctly typed callback when freeing syntax extensions.

--- src/plugin.c.orig
+++ src/plugin.c
@@ -1,6 +1,7 @@
 #include <stdlib.h>
 
 #include "plugin.h"
+#include "syntax_extension.h"
 
 extern cmark_mem CMARK_DEFAULT_MEM_ALLOCATOR;
 
@@ -23,7 +24,7 @@
 cmark_plugin_free(cmark_plugin *plugin) {
   cmark_llist_free_full(&CMARK_DEFAULT_MEM_ALLOCATOR,
                         plugin->syntax_extensions,
-                        (cmark_free_func) cmark_syntax_extension_free);
+                        cmark_syntax_extension_free_cb);
   CMARK_DEFAULT_MEM_ALLOCATOR.free(plugin);
 }
 
