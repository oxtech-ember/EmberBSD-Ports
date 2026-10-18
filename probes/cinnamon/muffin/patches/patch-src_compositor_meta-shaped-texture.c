$NetBSD$

Wayland profile: no GDK in the core; gdk_rectangle_intersect is
inlined as plain clamping arithmetic.

--- src/compositor/meta-shaped-texture.c.orig
+++ src/compositor/meta-shaped-texture.c
@@ -31,7 +31,6 @@
 #include "compositor/meta-shaped-texture-private.h"
 #include "core/boxes-private.h"
 
-#include <gdk/gdk.h>
 #include <math.h>
 
 #include "cogl/cogl.h"
@@ -708,7 +707,15 @@
               cairo_rectangle_int_t rect;
               cairo_region_get_rectangle (blended_tex_region, i, &rect);
 
-              if (!gdk_rectangle_intersect (&content_rect, &rect, &rect))
+              if (rect.x < content_rect.x)
+                rect.x = content_rect.x;
+              if (rect.y < content_rect.y)
+                rect.y = content_rect.y;
+              if (rect.x + rect.width > content_rect.x + content_rect.width)
+                rect.width = content_rect.x + content_rect.width - rect.x;
+              if (rect.y + rect.height > content_rect.y + content_rect.height)
+                rect.height = content_rect.y + content_rect.height - rect.y;
+              if (rect.width <= 0 || rect.height <= 0)
                 continue;
 
               paint_clipped_rectangle_node (stex, root_node,
