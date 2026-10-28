$NetBSD$

Origin: EmberBSD (AI-assisted); preserve OS portability and build routing.

--- platform.h.orig
+++ platform.h
@@ -1,8 +1,14 @@
 /* Unix platform.h for EK */
 
+#include <ctype.h>
+#include <errno.h>
 #include <stdio.h>
+#include <stdlib.h>
+#include <unistd.h>
 #include <sys/stat.h>
 
+#undef X_OK	/* namespace collision between kermit.h and unistd.h */
+
 #ifndef IBUFLEN
 #define IBUFLEN  4096			/* File input buffer size */
 #endif /* IBUFLEN */
