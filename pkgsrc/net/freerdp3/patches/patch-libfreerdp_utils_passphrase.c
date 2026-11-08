$NetBSD$

Include sys/wait.h for WIFEXITED and WEXITSTATUS.

--- libfreerdp/utils/passphrase.c.orig
+++ libfreerdp/utils/passphrase.c
@@ -74,6 +74,7 @@
 #include <sys/stat.h>
 #include <termios.h>
 #include <unistd.h>
+#include <sys/wait.h>
 #include <freerdp/utils/signal.h>
 
 #if defined(WINPR_HAVE_POLL_H) && !defined(__APPLE__)
