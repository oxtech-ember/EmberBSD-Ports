$NetBSD$

--- src/core/meta-context-main.c.orig	2026-09-15 17:26:39.000000000 +0300
+++ src/core/meta-context-main.c	2026-10-12 23:45:15.285604644 +0300
@@ -25,7 +25,7 @@
 #include <glib.h>
 #include <gio/gio.h>
 
-#ifdef HAVE_WAYLAND
+#if defined(HAVE_LIBSYSTEMD) && defined(HAVE_WAYLAND)
 #include <systemd/sd-login.h>
 #endif
 
@@ -173,6 +173,7 @@
   gboolean is_tty = FALSE;
   int ret, i;
 
+#ifdef HAVE_LIBSYSTEMD
   ret = sd_pid_get_session (0, &session_id);
   if (ret == 0 && session_id != NULL)
     {
@@ -207,6 +208,7 @@
         }
     }
   g_strfreev (sessions);
+#endif /* HAVE_LIBSYSTEMD */
 
   session_type_env = g_getenv ("XDG_SESSION_TYPE");
   if (session_type_is_supported (session_type_env))
