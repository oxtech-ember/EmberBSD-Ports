$NetBSD$

Resolve installed default paths from the actual component location.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- girepository/girparser.c.orig
+++ girepository/girparser.c
@@ -33,6 +33,8 @@
 #include "girmodule.h"
 #include "girnode.h"
 #include "gitypelib-internal.h"
+#include "gi-relocate-private.h"
+static const char gi_parser_anchor;
 
 #ifdef G_OS_UNIX
 #include <sys/socket.h> /* For socklen_t */
@@ -303,6 +305,8 @@
   const gchar *const *datadirs;
   const gchar *const *dir;
   char *path = NULL;
+  g_autofree char *relocated_gir = _g_ir_relocated_path (&gi_parser_anchor, GIR_DIR);
+  g_autofree char *relocated_data = _g_ir_relocated_path (&gi_parser_anchor, GOBJECT_INTROSPECTION_DATADIR);
 
   g_debug ("Looking for %s", girname);
   datadirs = g_get_system_data_dirs ();
@@ -349,13 +353,13 @@
       g_clear_pointer (&path, g_free);
     }
 
-  path = g_build_filename (GIR_DIR, girname, NULL);
+  path = g_build_filename (relocated_gir ? relocated_gir : GIR_DIR, girname, NULL);
   g_debug ("Trying %s from GIR_DIR", path);
   if (g_file_test (path, G_FILE_TEST_EXISTS | G_FILE_TEST_IS_REGULAR))
     return g_steal_pointer (&path);
   g_clear_pointer (&path, g_free);
 
-  path = g_build_filename (GOBJECT_INTROSPECTION_DATADIR, GIR_SUFFIX, girname, NULL);
+  path = g_build_filename (relocated_data ? relocated_data : GOBJECT_INTROSPECTION_DATADIR, GIR_SUFFIX, girname, NULL);
   g_debug ("Trying %s from DATADIR", path);
   if (g_file_test (path, G_FILE_TEST_EXISTS | G_FILE_TEST_IS_REGULAR))
     return g_steal_pointer (&path);
