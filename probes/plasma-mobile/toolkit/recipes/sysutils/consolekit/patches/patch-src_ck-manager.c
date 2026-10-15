$NetBSD: patch-src_ck-manager.c,v 1.1 2025/07/08 13:01:37 jperkin Exp $
Origin: EmberBSD (AI-assisted), local port; not submitted upstream.

Keep the GCC preprocessor fix and enforce privileged parameterized registration.

--- src/ck-manager.c.orig
+++ src/ck-manager.c
@@ -1361,7 +1361,7 @@
         return NULL;
 }
 
-#ifdef ENABLE_RBAC_SHUTDOWN
+#if !defined(HAVE_POLKIT) && defined(ENABLE_RBAC_SHUTDOWN)
 static gboolean
 check_rbac_permissions (CkManager             *manager,
                         GDBusMethodInvocation *context,
@@ -3252,10 +3252,20 @@
                                    GVariant              *parameters)
 {
         const char *sender;
+        uid_t       uid = 0;
+        pid_t       pid = 0;
 
         TRACE ();
 
         sender = g_dbus_method_invocation_get_sender (context);
+        if (!get_caller_info (CK_MANAGER (ckmanager), sender, &uid, &pid)) {
+                throw_error (context, CK_MANAGER_ERROR_GENERAL, _("Unable to get information about the calling process"));
+                return TRUE;
+        }
+        if (uid != 0) {
+                throw_error (context, CK_MANAGER_ERROR_INSUFFICIENT_PERMISSION, _("Only root may open a session with parameters"));
+                return TRUE;
+        }
         create_session_for_sender (CK_MANAGER (ckmanager), sender, parameters, context);
 
         return TRUE;
