$NetBSD$

Give the SIGTERM handler the signal handler prototype.

--- main.c.orig
+++ main.c
@@ -37,8 +37,9 @@
 }
 
 static void
-handle_sigterm_pid1()
+handle_sigterm_pid1(int sig)
 {
+    UNUSED_PARAMETER(sig);
     exit(143);
 }
 
