$NetBSD: patch-glib_tests_testing.c,v 1.2 2026/08/09 02:32:02 mef Exp $

revert the changes from 2.88.1 to 2.88.3
to fix F_DUPFD_CLOEXEC undefined issue

--- glib/tests/testing.c.orig
+++ glib/tests/testing.c
@@ -22,7 +22,6 @@
  * if advised of the possibility of such damage.
  */
 
-#define _POSIX_C_SOURCE 200809L  /* for F_DUPFD_CLOEXEC */
 
 #include "config.h"
 
@@ -33,6 +32,7 @@
 #define G_LOG_DOMAIN "testing"
 
 #include <glib.h>
+#define _POSIX_C_SOURCE 200809L  /* for F_DUPFD_CLOEXEC */
 #include <locale.h>
 #include <stdlib.h>
 #include <string.h>
