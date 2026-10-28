# Origin: EmberBSD (AI-assisted).
Use equivalent string indexing for the selected diagnostic suffix.

--- src/rcsrev.c.orig
+++ src/rcsrev.c
@@ -236,9 +236,9 @@
         revno,
         date ? " a date before " : "",
         date ? date2str (date, datebuf) : "",
-        author ? " and author " + (date ? 0 : 4) : "",
+        author ? &" and author "[date ? 0 : 4] : "",
         author ? author : "",
-        state ? " and state " + (date || author ? 0 : 4) : "",
+        state ? &" and state "[date || author ? 0 : 4] : "",
         state ? state : "");
 }
 
