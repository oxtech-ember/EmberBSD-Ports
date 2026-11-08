$NetBSD$

Resolve the NetBSD console alias to the active wsdisplay.

Getty EmberPlasma logs in on /dev/constty. That device is not a
/dev/ttyE node, so ConsoleKit left the session off seat0 and inactive.
Polkit then refuses the active-session authentication prompt.

--- tools/ck-collect-session-info.c.orig
+++ tools/ck-collect-session-info.c
@@ -394,7 +394,22 @@
 
         si->display_device = ck_process_stat_get_tty (stat);
         ck_process_stat_free (stat);
+        /* /dev/constty is the wsdisplay console alias, not a VT node. */
+        if (g_strcmp0 (si->display_device, "/dev/constty") == 0) {
+                int console_fd = open ("/dev/console", O_RDONLY | O_NOCTTY);
+                guint active = 0;
+                if (console_fd != -1 && ck_get_active_console_num (console_fd, &active)) {
+                        char *device = ck_get_console_device_for_num (active);
+                        if (device != NULL) {
+                                g_free (si->display_device);
+                                si->display_device = device;
+                        }
+                }
+                if (console_fd != -1) {
+                        close (console_fd);
+                }
+        }
 
         if (si->x11_display_device == NULL) {
                 /* If our DM set the display device we don't need to look
                  * it up here */
