Origin: EmberBSD (AI-assisted), local port; not submitted upstream.

Enforce the documented session-owner-or-root TakeControl contract.

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
