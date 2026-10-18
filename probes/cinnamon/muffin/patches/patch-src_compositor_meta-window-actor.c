$NetBSD$

Wayland profile: no GDK in the core; gdk_cairo_region is inlined
as plain cairo calls (same rectangle walk).

--- src/compositor/meta-window-actor.c.orig
+++ src/compositor/meta-window-actor.c
@@ -21,7 +21,6 @@
 
 #include "config.h"
 
-#include <gdk/gdk.h>
 #include <math.h>
 #include <string.h>
 
@@ -1007,7 +1006,14 @@
   cairo_surface_t *surface = cairo_image_surface_create (CAIRO_FORMAT_A8, width, height);
   cairo_t *cr = cairo_create (surface);
 
-  gdk_cairo_region (cr, region);
+  do { /* gdk_cairo_region replacement: add each rectangle */
+    int _n = cairo_region_num_rectangles (region);
+    for (int _i = 0; _i < _n; _i++) {
+      cairo_rectangle_int_t _r;
+      cairo_region_get_rectangle (region, _i, &_r);
+      cairo_rectangle (cr, _r.x, _r.y, _r.width, _r.height);
+    }
+  } while (0);
   cairo_fill (cr);
 
   cairo_surface_write_to_png (surface, filename);
