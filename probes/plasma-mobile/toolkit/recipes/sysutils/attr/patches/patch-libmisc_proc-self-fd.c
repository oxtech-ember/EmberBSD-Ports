$NetBSD$

Use native xattr calls in the private, single-threaded CLI backend.
Retain cwd, errno and explicit errors. libattr ABI is unchanged.
Origin: EmberBSD (AI-assisted).

--- libmisc/proc-self-fd.c.orig
+++ libmisc/proc-self-fd.c
@@ -18,6 +18,8 @@
 */
 
 #include "config.h"
+
+#ifndef __NetBSD__
 #include <unistd.h>
 #include <fcntl.h>
 #include <stdio.h>
@@ -90,3 +92,5 @@
 		return 0;
 	return 1;
 }
+
+#endif /* !__NetBSD__ */
