$NetBSD$

Pass ucs4_t code points as the unsigned long that %lx and %lX read.
On LP64 the upper half was otherwise undefined, so node identifiers
could differ between a node and its references.

--- tta/C/main/node_name_normalization.c.orig
+++ tta/C/main/node_name_normalization.c
@@ -236,12 +236,12 @@
 
   if (next_char <= 0xFFFF)
     {
-      xasprintf (&str, "%04lx", next_char);
+      xasprintf (&str, "%04lx", (unsigned long) next_char);
       text_append_n (result, "_", 1);
     }
   else
     {
-      xasprintf (&str, "%06lx", next_char);
+      xasprintf (&str, "%06lx", (unsigned long) next_char);
       text_append_n (result, "__", 2);
     }
   text_append (result, str);
