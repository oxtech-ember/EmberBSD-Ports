$NetBSD$

--- src/core/meta-context-main.c.orig	2025-03-04 22:59:55.000000000 +0300
+++ src/core/meta-context-main.c	2026-10-12 21:37:30.573556364 +0300
@@ -25,7 +25,7 @@
 #include <glib.h>
 #include <gio/gio.h>
 
-#ifdef HAVE_WAYLAND
+#if defined(HAVE_LIBSYSTEMD) && defined(HAVE_WAYLAND)
 #include <systemd/sd-login.h>
 #endif
 
@@ -170,6 +170,7 @@
   gboolean is_tty = FALSE;
   int ret, i;
 
+#ifdef HAVE_LIBSYSTEMD
   ret = sd_pid_get_session (0, &session_id);
   if (ret == 0 && session_id != NULL)
     {
@@ -204,6 +205,7 @@
         }
     }
   g_strfreev (sessions);
+#endif /* HAVE_LIBSYSTEMD */
 
   session_type_env = g_getenv ("XDG_SESSION_TYPE");
   if (session_type_is_supported (session_type_env))
