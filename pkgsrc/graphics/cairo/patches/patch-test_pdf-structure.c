$NetBSD: patch-test_pdf-structure.c,v 1.1 2023/11/14 13:48:19 wiz Exp $

Add header for WIFEXITED and WAITSTATUS.

--- test/pdf-structure.c.orig
+++ test/pdf-structure.c
@@ -29,6 +29,7 @@
 #include <stdio.h>
 #include <string.h>
 #include <stdlib.h>
+#include <sys/wait.h>
 
 #ifdef HAVE_UNISTD_H
 #include <unistd.h> /* __unix__ */
