$NetBSD$

NetBSD has no sys/prctl.h; the thread-name fallback keeps the
pid-based program name.

--- src/pipewire/pipewire.c.orig	2026-10-13
+++ src/pipewire/pipewire.c
@@ -7,7 +7,7 @@
 #include <unistd.h>
 #include <limits.h>
 #include <stdio.h>
-#if !defined(__FreeBSD__) && !defined(__MidnightBSD__) && !defined(__GNU__)
+#if !defined(__FreeBSD__) && !defined(__MidnightBSD__) && !defined(__GNU__) && !defined(__NetBSD__)
 #include <sys/prctl.h>
 #endif
 #include <pwd.h>
@@ -683,7 +683,7 @@
 		}
 	}
 #endif
-#if !defined(__FreeBSD__) && !defined(__MidnightBSD__) && !defined(__GNU__)
+#if !defined(__FreeBSD__) && !defined(__MidnightBSD__) && !defined(__GNU__) && !defined(__NetBSD__)
 	{
 		if (prctl(PR_GET_NAME, (unsigned long) name, 0, 0, 0) == 0) {
 			prgname = name;
