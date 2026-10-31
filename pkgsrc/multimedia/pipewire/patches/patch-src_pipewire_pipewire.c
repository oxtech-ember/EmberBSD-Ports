$NetBSD$

NetBSD has no sys/prctl.h; the thread-name fallback keeps the
pid-based program name. NetBSD has no EBADFD; use EBADF.

--- src/pipewire/pipewire.c.orig
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
@@ -15,6 +15,11 @@
 #include <dlfcn.h>
 #include <pthread.h>
 
+/* NetBSD has no EBADFD; pw_init() not called is a bad descriptor state. */
+#ifndef EBADFD
+#define EBADFD EBADF
+#endif
+
 #include <locale.h>
 #include <libintl.h>
 
@@ -683,7 +688,7 @@
 		}
 	}
 #endif
-#if !defined(__FreeBSD__) && !defined(__MidnightBSD__) && !defined(__GNU__)
+#if !defined(__FreeBSD__) && !defined(__MidnightBSD__) && !defined(__GNU__) && !defined(__NetBSD__)
 	{
 		if (prctl(PR_GET_NAME, (unsigned long) name, 0, 0, 0) == 0) {
 			prgname = name;
