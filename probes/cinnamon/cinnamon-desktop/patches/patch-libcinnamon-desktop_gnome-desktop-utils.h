$NetBSD$

The Wayland profile carries no GTK3; this header declares neither
Gdk nor Gtk API. Replace the dead includes with the gio/unistd
headers utils.c needs (they used to arrive transitively via gtk).

--- libcinnamon-desktop/gnome-desktop-utils.h.orig	2026-10-18
+++ libcinnamon-desktop/gnome-desktop-utils.h
@@ -34,8 +34,8 @@
 #include <glib.h>
 #include <glib-object.h>
 
-#include <gdk/gdk.h>
-#include <gtk/gtk.h>
+#include <gio/gio.h>
+#include <unistd.h>
 #include <pwd.h>
 
 G_BEGIN_DECLS
