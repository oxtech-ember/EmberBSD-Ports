# $NetBSD$

Preserve desktop-app cmark-gfm hardening changes from upstream fork
3b2bbdc028c1747d1e50d1a32c7f7c61e58c8133,
48a0cf99150a42617762ae67cae65f9a5b88647a and
d7d4a24a9ebfa7581994ea6df0297662bfeaf413.

--- extensions/tasklist.c.orig
+++ extensions/tasklist.c
@@ -89,7 +89,19 @@
   cmark_parser_advance_offset(parser, (char *)input, 3, false);
 
   // Either an upper or lower case X means the task is completed.
-  parent_container->as.list.checked = (strstr((char*)input, "[x]") || strstr((char*)input, "[X]"));
+  // Look only inside the prefix scan_tasklist just matched: that prefix
+  // is spaces, a list marker, spaces and the "[ ]"/"[x]" token, so any
+  // "[x]"-shaped substring there is the marker itself. The item text may
+  // legitimately contain "[x]", which must not complete the task.
+  bool checked = false;
+  for (bufsize_t i = 0; i + 2 < matched; i++) {
+    if (input[i] == '[' && (input[i + 1] == 'x' || input[i + 1] == 'X') &&
+        input[i + 2] == ']') {
+      checked = true;
+      break;
+    }
+  }
+  parent_container->as.list.checked = checked;
 
   return NULL;
 }
