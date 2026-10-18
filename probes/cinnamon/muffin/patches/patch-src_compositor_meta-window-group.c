$NetBSD$

Wayland profile: the GDK include is dead weight here (no Gdk API
referenced with the GTK3 decoration stack stubbed).

--- src/compositor/meta-window-group.c.orig
+++ src/compositor/meta-window-group.c
@@ -2,7 +2,6 @@
 
 #include "config.h"
 
-#include <gdk/gdk.h>
 #include <math.h>
 
 #include "compositor/clutter-utils.h"
