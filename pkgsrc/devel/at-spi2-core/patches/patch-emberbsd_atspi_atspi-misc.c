$NetBSD$

Resolve prefix-owned paths from the installed Darwin image.

--- atspi/atspi-misc.c.orig
+++ atspi/atspi-misc.c
@@ -29,6 +29,9 @@
  */
 
 #include "atspi-private.h"
+#ifdef ATSPI_DARWIN_RELOCATABLE
+#include "../darwin-install-path.h"
+#endif
 #ifdef HAVE_X11
 #include "X11/Xlib.h"
 #endif
@@ -179,7 +182,13 @@
     {
       gettext_initialized = TRUE;
       setlocale (LC_ALL, "");
+#ifdef ATSPI_DARWIN_RELOCATABLE
+      g_autofree gchar *locale_dir = atspi_install_path (ATSPI_LOCALE_SUBDIR);
+      if (locale_dir != NULL)
+        bindtextdomain (GETTEXT_PACKAGE, locale_dir);
+#else
       bindtextdomain (GETTEXT_PACKAGE, ATSPI_LOCALEDIR);
+#endif
       bind_textdomain_codeset (GETTEXT_PACKAGE, "UTF-8");
     }
 }
