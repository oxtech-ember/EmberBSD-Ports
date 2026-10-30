Origin: Gleb Popov / FreeBSD Ports commit 12b84b980b45573c93be5382a274dbe872a1eb73.
https://github.com/freebsd/freebsd-ports/commit/12b84b980b45573c93be5382a274dbe872a1eb73
Adapted for EmberBSD (AI-assisted): use mutable pointers for allocated strings.
ConsoleKit 2.0 database/session IDs differ from D-Bus object paths.
Not submitted upstream.

--- src/polkit/polkitunixsession.c.orig
+++ src/polkit/polkitunixsession.c
@@ -360,6 +360,7 @@
   PolkitUnixSession *session = POLKIT_UNIX_SESSION (subject);
   GDBusConnection *connection;
   GVariant *result;
+  gchar *session_path = NULL;
   gboolean ret;
 
   ret = FALSE;
@@ -368,9 +369,12 @@
   if (connection == NULL)
     goto out;
 
+  if (strncmp (session->session_id, "/org/freedesktop/ConsoleKit", strlen ("/org/freedesktop/ConsoleKit") ))
+    session_path = g_build_path("/", "/org/freedesktop/ConsoleKit", session->session_id, NULL);
+
   result = g_dbus_connection_call_sync (connection,
                                         "org.freedesktop.ConsoleKit",           /* name */
-                                        session->session_id,                    /* object path */
+                                        session_path ? session_path : session->session_id,                    /* object path */
                                         "org.freedesktop.ConsoleKit.Session",   /* interface name */
                                         "GetUser",                              /* method */
                                         NULL, /* parameters */
@@ -379,6 +383,7 @@
                                         -1,
                                         cancellable,
                                         error);
+  g_free (session_path);
   if (result == NULL)
     goto out;
 
@@ -468,6 +473,7 @@
   PolkitUnixSession *session = POLKIT_UNIX_SESSION (initable);
   GDBusConnection *connection;
   GVariant *result;
+  const gchar* session_path;
   gboolean ret;
 
   connection = NULL;
@@ -498,7 +504,8 @@
   if (result == NULL)
     goto out;
 
-  g_variant_get (result, "(o)", &session->session_id);
+  g_variant_get (result, "(&o)", &session_path);
+  session->session_id = g_path_get_basename (session_path);
   g_variant_unref (result);
 
   ret = TRUE;
