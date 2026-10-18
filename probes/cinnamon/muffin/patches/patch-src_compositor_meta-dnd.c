$NetBSD$

Wayland profile: the GDK include is dead weight here (no Gdk API
referenced with the GTK3 decoration stack stubbed).

--- src/compositor/meta-dnd.c.orig
+++ src/compositor/meta-dnd.c
@@ -19,7 +19,6 @@
 
 #include "config.h"
 
-#include <gdk/gdkx.h>
 
 #include "clutter/x11/clutter-x11.h"
 #include "meta/meta-backend.h"
