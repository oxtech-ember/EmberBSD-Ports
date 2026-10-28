# Origin: EmberBSD (AI-assisted).
Allow two diff labels as supported by the OS rcsdiff interface.

--- src/rcsdiff.c.orig
+++ src/rcsdiff.c
@@ -190,7 +190,7 @@
           case 'W':
             if (DIFF_L
                 && c == 'L'
-                && ++file_labels == 2)
+                && file_labels++ == 2)
               PFATAL ("too many -L options");
             *dcp++ = c;
             if (*a)
