Origin: EmberBSD (AI-assisted), local port; not submitted upstream.

Enforce owner-or-root control and retain canonical device FD ownership.
Only the outgoing duplicate belongs to the generated D-Bus reply.

--- src/ck-session.c.orig
+++ src/ck-session.c
@@ -1712,6 +1712,11 @@
                 return TRUE;
         }
 
+        if (uid != 0 && uid != console_kit_session_get_unix_user (object)) {
+                throw_error (invocation, CK_SESSION_ERROR_INSUFFICIENT_PERMISSION, _("Only the session owner or root may take control"));
+                return TRUE;
+        }
+
         if (g_strcmp0 (session->priv->session_controller, sender) == 0)
         {
                 /* The current session controller is trying to take control
@@ -1845,6 +1850,8 @@
         const gchar *sender = g_dbus_method_invocation_get_sender (invocation);
         gint         fd = -1;
         GUnixFDList *out_fd_list = NULL;
+        GError      *error = NULL;
+        gint         handle;
 
 
         TRACE ();
@@ -1870,16 +1877,28 @@
 
         fd = ck_device_get_fd (device);
 
-        if (fd == -1) {
+        if (fd < 0) {
+                ck_session_remove_device (session, device);
+                g_object_unref (device);
                 throw_error (invocation, CK_SESSION_ERROR_NOT_SUPPORTED, _("Failed to get file descriptor for device"));
                 return TRUE;
         }
 
-        out_fd_list = g_unix_fd_list_new_from_array (&fd, 1);
+        out_fd_list = g_unix_fd_list_new ();
+        handle = g_unix_fd_list_append (out_fd_list, fd, &error);
+        if (handle < 0) {
+                g_clear_error (&error);
+                g_clear_object (&out_fd_list);
+                ck_session_remove_device (session, device);
+                g_object_unref (device);
+                throw_error (invocation, CK_SESSION_ERROR_FAILED, _("Failed to duplicate file descriptor for device"));
+                return TRUE;
+        }
 
         console_kit_session_complete_take_device (object, invocation,
-                                                  out_fd_list, g_variant_new_handle (0),
-                                                  console_kit_session_get_active (object));
+                                                  out_fd_list, g_variant_new_handle (handle),
+                                                  !ck_device_get_active (device));
+        g_clear_object (&out_fd_list);
         return TRUE;
 }
 
