# $NetBSD$

Preserve desktop-app cmark-gfm hardening changes from upstream fork
3b2bbdc028c1747d1e50d1a32c7f7c61e58c8133,
48a0cf99150a42617762ae67cae65f9a5b88647a and
d7d4a24a9ebfa7581994ea6df0297662bfeaf413.

--- extensions/autolink.c.orig
+++ extensions/autolink.c
@@ -93,6 +93,12 @@
       link_end--;
       break;
     case ';': {
+      // A ';' this early leaves no room for an "&entity;" before it; the
+      // early exit also keeps the subtraction below from wrapping size_t.
+      if (link_end <= 2) {
+        link_end--;
+        break;
+      }
       size_t new_end = link_end - 2;
 
       while (new_end > 0 && cmark_isalpha(data[new_end]))
@@ -299,7 +305,7 @@
 static bool validate_protocol(const char protocol[], uint8_t *data, size_t rewind, size_t max_rewind) {
   size_t len = strlen(protocol);
 
-  if (len > (max_rewind - rewind)) {
+  if (len + rewind > max_rewind) {
     return false;
   }
 
@@ -312,7 +318,7 @@
     return true;
   }
 
-  char prev_char = data[-((ptrdiff_t)rewind) - len - 1];
+  char prev_char = data[-(ptrdiff_t)(rewind + len + 1)];
 
   // Make sure the character before the protocol is non-alphanumeric
   return !cmark_isalnum(prev_char);
