Origin: EmberBSD (AI-assisted), local port; not submitted upstream.

Preserve child status and reject execution when session registration fails.

--- tools/ck-launch-session.c.orig
+++ tools/ck-launch-session.c
@@ -41,6 +41,7 @@
 #define _PATH_BSHELL "/bin/sh"
 #endif
 
+#include <errno.h>
 #include <stdlib.h>
 #include <syslog.h>
 #include <unistd.h>
@@ -114,7 +115,7 @@
                 dbus_error_init (&error);
                 ret = service == NULL
                         ? ck_connector_open_session (ckc, &error)
-                        : ck_connector_open_session_with_parameters (ckc, &error, "session-service", &service);
+                        : ck_connector_open_session_with_parameters (ckc, &error, "session-service", &service, NULL);
 
                 if (ret) {
                         const char *runtime_dir = NULL;
@@ -122,7 +123,7 @@
                         switch (pid) {
                         case -1:
                                 syslog (LOG_ERR, "error forking child");
-                                break;
+                                exit (EXIT_FAILURE);
                         case 0:
                                 setenv ("XDG_SESSION_COOKIE",
                                        ck_connector_get_cookie (ckc), 1);
@@ -133,18 +134,38 @@
                                 }
                                 break;
                         default:
-                                waitpid (pid, &status, 0);
-                                exit (status);
+                                while (waitpid (pid, &status, 0) < 0) {
+                                        if (errno != EINTR) {
+                                                syslog (LOG_ERR, "error waiting for child");
+                                                exit (EXIT_FAILURE);
+                                        }
+                                }
+                                if (WIFEXITED (status)) {
+                                        exit (WEXITSTATUS (status));
+                                }
+                                if (WIFSIGNALED (status)) {
+                                        exit (128 + WTERMSIG (status));
+                                }
+                                exit (EXIT_FAILURE);
                                 break;
                         }
                 } else {
                         syslog (LOG_ERR, "error connecting to ConsoleKit");
+                        g_printerr ("Unable to register ConsoleKit session: %s\n",
+                                    dbus_error_is_set (&error) ? error.message : "no error returned");
+                        if (dbus_error_is_set (&error)) {
+                                dbus_error_free (&error);
+                        }
+                        ck_connector_unref (ckc);
+                        exit (EXIT_FAILURE);
                 }
         } else {
                 syslog (LOG_ERR, "error setting up to connection to ConsoleKit");
+                g_printerr ("Unable to allocate ConsoleKit connector\n");
+                exit (EXIT_FAILURE);
         }
 
-        if (command[0] != NULL) {
+        if (command != NULL && command[0] != NULL) {
                 execvp (command[0], command);
         } else {
                 shell = getenv ("SHELL");
