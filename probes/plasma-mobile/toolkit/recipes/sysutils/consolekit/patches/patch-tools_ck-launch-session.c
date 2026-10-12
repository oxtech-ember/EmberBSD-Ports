Preserve child exit status, handle interrupted waits and use the default shell safely.
Terminate the optional session-service parameter list.
Origin: EmberBSD (AI-assisted), not submitted upstream.

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
@@ -133,8 +134,19 @@
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
@@ -144,7 +156,7 @@
                 syslog (LOG_ERR, "error setting up to connection to ConsoleKit");
         }
 
-        if (command[0] != NULL) {
+        if (command != NULL && command[0] != NULL) {
                 execvp (command[0], command);
         } else {
                 shell = getenv ("SHELL");
