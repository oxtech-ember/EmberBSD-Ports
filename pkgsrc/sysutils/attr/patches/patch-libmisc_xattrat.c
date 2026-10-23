$NetBSD$

Use native xattr calls in the private, single-threaded CLI backend.
Retain cwd, errno and explicit errors. libattr ABI is unchanged.
Origin: EmberBSD (AI-assisted).

--- libmisc/xattrat.c.orig
+++ libmisc/xattrat.c
@@ -18,6 +18,8 @@
 */
 
 #include "config.h"
+
+#ifndef __NetBSD__
 #include <linux/xattr.h>
 #include <sys/syscall.h>
 #include <unistd.h>
@@ -85,3 +87,5 @@
 	return -1;
 #endif
 }
+
+#endif /* !__NetBSD__ */
