$NetBSD: patch-glib_gspawn-posix.c,v 1.1 2024/10/22 09:50:39 adam Exp $

Retain the pkgsrc DragonFly environ declaration. GLib 2.90.1 now handles
FreeBSD upstream through dlsym; preserve that implementation.
Set environ as a weak symbol (thanks to Joerg).

--- glib/gspawn-posix.c.orig
+++ glib/gspawn-posix.c
@@ -107,6 +107,8 @@
  */
 #include <dlfcn.h>
 #define environ (*((char***)dlsym(RTLD_DEFAULT, "environ")))
+#elif defined(__DragonFly__)
+extern __attribute__((__weak__)) char **environ;
 #else
 extern char **environ;
 #endif
