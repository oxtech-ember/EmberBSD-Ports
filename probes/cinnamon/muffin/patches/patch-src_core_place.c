$NetBSD$

Wayland profile: the GDK include is dead weight here (no Gdk API
referenced with the GTK3 decoration stack stubbed).

--- src/core/place.c.orig
+++ src/core/place.c
@@ -26,7 +26,6 @@
 
 #include "core/place.h"
 
-#include <gdk/gdk.h>
 #include <math.h>
 #include <stdlib.h>
 
