$NetBSD$

The Wayland profile carries no GTK3/GDK; the pointer query uses the
clutter seat unconditionally (the X11-server branch belonged to the
stubbed decoration stack).

--- src/backends/meta-cursor-tracker.c.orig
+++ src/backends/meta-cursor-tracker.c
@@ -31,8 +31,8 @@
 
 #include "backends/meta-cursor-tracker-private.h"
 
-#include <gdk/gdk.h>
-#include <gdk/gdkx.h>
+/* EmberBSD Wayland profile: the GDK X11 pointer query belongs to the
+ * GTK3 stack; the Wayland compositor path uses the clutter seat. */
 #include <string.h>
 
 #include "backends/meta-backend-private.h"
@@ -412,34 +412,6 @@
 }
 
 static void
-get_pointer_position_gdk (graphene_point_t *point,
-                          int              *mods)
-
-{
-  GdkSeat *gseat;
-  GdkDevice *gdevice;
-  GdkScreen *gscreen;
-  double x, y;
-
-  gseat = gdk_display_get_default_seat (gdk_display_get_default ());
-  gdevice = gdk_seat_get_pointer (gseat);
-
-  /* Even if point is NULL we need this to get gscreen */
-  gdk_device_get_position_double (gdevice, &gscreen, &x, &y);
-
-  if (point)
-    {
-      point->x = x;
-      point->y = y;
-    }
-
-  if (mods)
-    gdk_device_get_state (gdevice,
-                          gdk_screen_get_root_window (gscreen),
-                          NULL, (GdkModifierType*)mods);
-}
-
-static void
 get_pointer_position_clutter (graphene_point_t *point,
                               int              *mods)
 {
@@ -466,10 +438,7 @@
      OTOH, on wayland we can't use GDK, because that only sees the events
      we forward to xwayland.
   */
-  if (meta_is_wayland_compositor ())
-    get_pointer_position_clutter (coords, (int *) mods);
-  else
-    get_pointer_position_gdk (coords, (int *) mods);
+  get_pointer_position_clutter (coords, (int *) mods);
 }
 
 gboolean
