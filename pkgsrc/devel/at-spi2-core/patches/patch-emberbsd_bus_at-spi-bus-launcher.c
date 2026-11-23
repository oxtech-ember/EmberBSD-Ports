$NetBSD$

Resolve prefix-owned paths from the installed Darwin image.

--- bus/at-spi-bus-launcher.c.orig
+++ bus/at-spi-bus-launcher.c
@@ -21,6 +21,9 @@
  */
 
 #include "config.h"
+#ifdef ATSPI_DARWIN_RELOCATABLE
+#include "../darwin-install-path.h"
+#endif
 
 #include <signal.h>
 #include <string.h>
@@ -348,6 +351,14 @@
 ensure_a11y_bus_daemon (A11yBusLauncher *app, char *config_path)
 {
   char *address_param;
+#ifdef ATSPI_PREFIX_DBUS_DAEMON
+  g_autofree gchar *daemon = atspi_install_path (DBUS_DAEMON);
+
+  if (daemon == NULL)
+    return FALSE;
+#else
+  char *daemon = DBUS_DAEMON;
+#endif
 
   if (app->socket_name)
     {
@@ -365,7 +376,7 @@
 
   char *print_address_fd_param = g_strdup_printf ("%d", app->pipefd[1]);
 
-  char *argv[] = { DBUS_DAEMON, config_path, "--nofork", "--print-address", print_address_fd_param, address_param, NULL };
+  char *argv[] = { daemon, config_path, "--nofork", "--print-address", print_address_fd_param, address_param, NULL };
   gint source_fds[1] = { app->pipefd[1] };
   gint target_fds[1] = { app->pipefd[1] };
   G_STATIC_ASSERT (G_N_ELEMENTS (source_fds) == G_N_ELEMENTS (target_fds));
@@ -626,10 +637,20 @@
   if (app->a11y_bus_pid != 0)
     return FALSE;
 
+#ifdef ATSPI_DARWIN_RELOCATABLE
+  g_autofree gchar *configured = atspi_install_path (ATSPI_SYSCONF_SUBDIR "/at-spi2/accessibility.conf");
+  g_autofree gchar *example = atspi_install_path ("share/examples/at-spi2-core/at-spi2/accessibility.conf");
+  if (configured == NULL || example == NULL)
+    return FALSE;
+  g_autofree gchar *argument = g_strconcat ("--config-file=",
+      g_file_test (configured, G_FILE_TEST_EXISTS) ? configured : example, NULL);
+  config_path = argument;
+#else
   if (g_file_test (SYSCONFDIR "/at-spi2/accessibility.conf", G_FILE_TEST_EXISTS))
     config_path = "--config-file=" SYSCONFDIR "/at-spi2/accessibility.conf";
   else
     config_path = "--config-file=" DATADIR "/defaults/at-spi2/accessibility.conf";
+#endif
 
   xdg_runtime_dir = g_get_user_runtime_dir ();
   if (xdg_runtime_dir)
