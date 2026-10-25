$NetBSD$

Origin: EmberBSD (AI-assisted). Correct GTK-Doc closure metadata so
GObject Introspection exposes the desktop application launch callbacks.

--- libmenu/gmenu-desktopappinfo.c.orig
+++ libmenu/gmenu-desktopappinfo.c
@@ -729,10 +729,11 @@
  * @launch_context: (nullable): a #GAppLaunchContext
  * @spawn_flags: #GSpawnFlags, used for each process
- * @user_setup: (scope async) (nullable): a #GSpawnChildSetupFunc, used once
- *     for each process.
- * @user_setup_data: (closure user_setup) (nullable): User data for @user_setup
- * @pid_callback: (scope call) (nullable): Callback for child processes
- * @pid_callback_data: (closure pid_callback) (nullable): User data for @callback
+ * @user_setup: (scope async) (closure user_setup_data) (nullable):
+ *     a #GSpawnChildSetupFunc, used once for each process.
+ * @user_setup_data: (nullable): User data for @user_setup
+ * @pid_callback: (scope call) (closure pid_callback_data) (nullable):
+ *     Callback for child processes
+ * @pid_callback_data: (nullable): User data for @callback
  * @error: return location for a #GError, or %NULL
  *
  * This function performs the equivalent of g_app_info_launch_uris(),
