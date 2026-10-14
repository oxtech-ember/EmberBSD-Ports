$NetBSD$

glibc-only 'uint' type; use unsigned int. Origin: EmberBSD (AI-assisted).

--- src/core/window-private.h	2026-09-15 17:26:39.000000000 +0300
+++ src/core/window-private.h	2026-10-14 11:21:49.269368556 +0300
@@ -528,7 +528,7 @@
   guint placed : 1;
 
   /* Have this window been positioned? */
-  uint unconstrained_rect_valid : 1;
+  unsigned int unconstrained_rect_valid : 1;
 
   /* Has this window not ever been shown yet? */
   guint showing_for_first_time : 1;
