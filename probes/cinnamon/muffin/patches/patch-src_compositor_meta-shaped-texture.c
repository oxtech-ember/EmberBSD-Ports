$NetBSD$

Wayland profile: no GDK in the core; gdk_rectangle_intersect is
inlined as a proper corner-clamped intersection (both x/y shift and
size shrink, matching the GDK semantics).

--- src/compositor/meta-shaped-texture.c.orig
+++ src/compositor/meta-shaped-texture.c
@@ -31,7 +31,6 @@
 #include "compositor/meta-shaped-texture-private.h"
 #include "core/boxes-private.h"
 
-#include <gdk/gdk.h>
 #include <math.h>
 
 #include "cogl/cogl.h"
@@ -708,7 +707,19 @@
               cairo_rectangle_int_t rect;
               cairo_region_get_rectangle (blended_tex_region, i, &rect);
 
-              if (!gdk_rectangle_intersect (&content_rect, &rect, &rect))
+              /* gdk_rectangle_intersect replacement: clamp both corners,
+               * so the result never extends past either input. */
+              gint ix = MAX (rect.x, content_rect.x);
+              gint iy = MAX (rect.y, content_rect.y);
+              gint ix2 = MIN (rect.x + rect.width,
+                              content_rect.x + content_rect.width);
+              gint iy2 = MIN (rect.y + rect.height,
+                              content_rect.y + content_rect.height);
+              rect.x = ix;
+              rect.y = iy;
+              rect.width = ix2 - ix;
+              rect.height = iy2 - iy;
+              if (rect.width <= 0 || rect.height <= 0)
                 continue;
 
               paint_clipped_rectangle_node (stex, root_node,
