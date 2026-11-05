$NetBSD$

Resolve installed default paths from the actual component location.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- girepository/girepository.c.orig
+++ girepository/girepository.c
@@ -33,6 +33,8 @@
 #include "girepository.h"
 #include "gitypelib-internal.h"
 #include "girepository-private.h"
+#include "gi-relocate-private.h"
+static const char gi_repository_anchor;
 
 /**
  * SECTION:girepository
@@ -194,6 +196,7 @@
   if (typelib_search_path == NULL)
     {
       const char *libdir;
+      g_autofree char *relocated_libdir = NULL;
       char *typelib_dir;
       const gchar *type_lib_path_env;
 
@@ -222,7 +225,8 @@
           g_free (custom_dirs);
         }
 
-      libdir = GOBJECT_INTROSPECTION_LIBDIR;
+      relocated_libdir = _g_ir_relocated_path (&gi_repository_anchor, GOBJECT_INTROSPECTION_LIBDIR);
+      libdir = relocated_libdir ? relocated_libdir : GOBJECT_INTROSPECTION_LIBDIR;
 
       typelib_dir = g_build_filename (libdir, "girepository-1.0", NULL);
 
