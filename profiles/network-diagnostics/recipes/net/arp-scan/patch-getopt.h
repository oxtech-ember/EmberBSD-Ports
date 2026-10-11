$NetBSD$

--- getopt.h.orig	2020-04-05 16:12:00.000000000 +0000
+++ getopt.h
@@ -144,7 +144,7 @@
    errors, only prototype getopt for the GNU C library.  */
 extern int getopt (int ___argc, char *const *___argv, const char *__shortopts);
 # else /* not __GNU_LIBRARY__ */
-extern int getopt ();
+#include <unistd.h>
 # endif /* __GNU_LIBRARY__ */
 
 # ifndef __need_getopt

