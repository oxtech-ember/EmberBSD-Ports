Origin: Gleb Popov / FreeBSD Ports commit 12b84b980b45573c93be5382a274dbe872a1eb73.
https://github.com/freebsd/freebsd-ports/commit/12b84b980b45573c93be5382a274dbe872a1eb73
Adapted for EmberBSD (AI-assisted): use mutable pointers for allocated strings.
ConsoleKit 2.0 database/session IDs differ from D-Bus object paths.
Not submitted upstream.

--- src/polkitbackend/polkitbackendsessionmonitor.c.orig
+++ src/polkitbackend/polkitbackendsessionmonitor.c
@@ -384,7 +384,8 @@
 
   if (POLKIT_IS_UNIX_PROCESS (subject))
     {
-      const gchar *session_id;
+      const gchar *session_path;
+      gchar *session_id;
       GVariant *result;
       result = g_dbus_connection_call_sync (monitor->system_bus,
                                             "org.freedesktop.ConsoleKit",
@@ -399,14 +400,17 @@
                                             error);
       if (result == NULL)
         goto out;
-      g_variant_get (result, "(&o)", &session_id);
+      g_variant_get (result, "(&o)", &session_path);
+      session_id = g_path_get_basename (session_path);
       session = polkit_unix_session_new (session_id);
+      g_free (session_id);
       g_variant_unref (result);
     }
   else if (POLKIT_IS_SYSTEM_BUS_NAME (subject))
     {
       guint32 pid;
-      const gchar *session_id;
+      const gchar *session_path;
+      gchar *session_id;
       GVariant *result;
 
       result = g_dbus_connection_call_sync (monitor->system_bus,
@@ -438,8 +442,10 @@
                                             error);
       if (result == NULL)
         goto out;
-      g_variant_get (result, "(&o)", &session_id);
+      g_variant_get (result, "(&o)", &session_path);
+      session_id = g_path_get_basename (session_path);
       session = polkit_unix_session_new (session_id);
+      g_free (session_id);
       g_variant_unref (result);
     }
   else
