diff --git a/src/ui/ui.c b/src/ui/ui.c
index 8357a80..2c9e9f2 100644
--- src/ui/ui.c.orig
+++ b/src/ui/ui.c
@@ -1,278 +1,208 @@
 /* -*- mode: C; c-file-style: "gnu"; indent-tabs-mode: nil; -*- */
-
-/* Mutter interface for talking to GTK+ UI module */
-
 /*
- * Copyright (C) 2002 Havoc Pennington
- *
- * This program is free software; you can redistribute it and/or
- * modify it under the terms of the GNU General Public License as
- * published by the Free Software Foundation; either version 2 of the
- * License, or (at your option) any later version.
+ * EmberBSD Wayland profile: minimal MetaUI implementation.
  *
- * This program is distributed in the hope that it will be useful, but
- * WITHOUT ANY WARRANTY; without even the implied warranty of
- * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
- * General Public License for more details.
+ * The GTK3 server-side decoration stack (upstream ui.c, frames.c,
+ * theme.c) is not built on this platform. The functions below keep
+ * the X11 display code compiling and linkable; they are no-ops, so
+ * X11 clients on the Wayland session render without server-side
+ * decorations (client-side decorations only).
  *
- * You should have received a copy of the GNU General Public License
- * along with this program; if not, see <http://www.gnu.org/licenses/>.
+ * Copyright (C) 2026 EmberBSD contributors
+ * SPDX-License-Identifier: GPL-2.0-or-later
  */
 
 #include "config.h"
 
-#include <cairo-xlib.h>
-#include <stdlib.h>
+#include <X11/Xlib.h>
+#include <cairo.h>
 #include <string.h>
 
-#include "meta/prefs.h"
-#include "meta/util.h"
+#include "core/util-private.h"
+#include "meta/common.h"
+#include "meta/theme.h"
+#include "meta/types.h"
 #include "ui/frames.h"
-#include "ui/theme-private.h"
 #include "ui/ui.h"
-#include "x11/meta-x11-display-private.h"
-#include "x11/meta-x11-window-control.h"
 
 struct _MetaUI
 {
-  Display *xdisplay;
-  MetaFrames *frames;
-
-  /* For double-click tracking */
-  gint button_click_number;
-  Window button_click_window;
-  int button_click_x;
-  int button_click_y;
-  guint32 button_click_time;
+  MetaX11Display *x11_display;
 };
 
 MetaUI *
 meta_ui_new (MetaX11Display *x11_display)
 {
-  MetaUI *ui;
-
-  g_assert (x11_display->gdk_display == gdk_display_get_default ());
-
-  ui = g_new0 (MetaUI, 1);
-  ui->xdisplay = x11_display->xdisplay;
-
-  ui->frames = meta_frames_new (x11_display);
-  /* GTK+ needs the frame-sync protocol to work in order to properly
-   * handle style changes. This means that the dummy widget we create
-   * to get the style for title bars actually needs to be mapped
-   * and fully tracked as a MetaWindow. Horrible, but mostly harmless -
-   * the window is a 1x1 overide redirect window positioned offscreen.
-   */
-  gtk_widget_show (GTK_WIDGET (ui->frames));
-
-  g_object_set_data (G_OBJECT (x11_display->gdk_display), "meta-ui", ui);
-
+  MetaUI *ui = g_new0 (MetaUI, 1);
+  ui->x11_display = x11_display;
   return ui;
 }
 
 void
 meta_ui_free (MetaUI *ui)
 {
-  GdkDisplay *gdk_display;
-
-  gtk_widget_destroy (GTK_WIDGET (ui->frames));
-
-  gdk_display = gdk_x11_lookup_xdisplay (ui->xdisplay);
-  g_object_set_data (G_OBJECT (gdk_display), "meta-ui", NULL);
-
   g_free (ui);
 }
 
-static void
-set_background_none (Display *xdisplay,
-                     Window   xwindow)
+void
+meta_ui_theme_get_frame_borders (MetaUI          *ui,
+                                 MetaFrameType    type,
+                                 MetaFrameFlags   flags,
+                                 MetaFrameBorders *borders)
 {
-  XSetWindowAttributes attrs;
-
-  attrs.background_pixmap = None;
-  XChangeWindowAttributes (xdisplay, xwindow,
-                           CWBackPixmap, &attrs);
+  if (borders != NULL)
+    memset (borders, 0, sizeof (*borders));
 }
 
 MetaUIFrame *
-meta_ui_create_frame (MetaUI *ui,
-                      Display *xdisplay,
-                      MetaWindow *meta_window,
-                      Visual *xvisual,
-                      gint x,
-                      gint y,
-                      gint width,
-                      gint height,
-                      gulong *create_serial)
+meta_ui_create_frame (MetaUI      *ui,
+                      Display     *xdisplay,
+                      MetaWindow  *meta_window,
+                      Visual      *xvisual,
+                      gint         x,
+                      gint         y,
+                      gint         width,
+                      gint         height,
+                      gulong      *create_serial)
 {
-  GdkDisplay *display = gdk_x11_lookup_xdisplay (xdisplay);
-  GdkScreen *screen;
-  GdkWindowAttr attrs;
-  gint attributes_mask;
-  GdkWindow *window;
-  GdkVisual *visual;
-
-  screen = gdk_display_get_default_screen (display);
-
-  /* Default depth/visual handles clients with weird visuals; they can
-   * always be children of the root depth/visual obviously, but
-   * e.g. DRI games can't be children of a parent that has the same
-   * visual as the client.
-   */
-  if (!xvisual)
-    visual = gdk_screen_get_system_visual (screen);
-  else
-    {
-      visual = gdk_x11_screen_lookup_visual (screen,
-                                             XVisualIDFromVisual (xvisual));
-    }
-
-  attrs.title = NULL;
-
-  attrs.event_mask = GDK_EXPOSURE_MASK;
-  attrs.x = x;
-  attrs.y = y;
-  attrs.wclass = GDK_INPUT_OUTPUT;
-  attrs.visual = visual;
-  attrs.window_type = GDK_WINDOW_CHILD;
-  attrs.cursor = NULL;
-  attrs.wmclass_name = NULL;
-  attrs.wmclass_class = NULL;
-  attrs.override_redirect = FALSE;
-
-  attrs.width  = width;
-  attrs.height = height;
-
-  attributes_mask = GDK_WA_X | GDK_WA_Y | GDK_WA_VISUAL;
-
-  /* We make an assumption that gdk_window_new() is going to call
-   * XCreateWindow as it's first operation; this seems to be true currently
-   * as long as you pass in a colormap.
-   */
-  if (create_serial)
-    *create_serial = XNextRequest (xdisplay);
-  window =
-    gdk_window_new (gdk_screen_get_root_window(screen),
-		    &attrs, attributes_mask);
-
-  gdk_window_resize (window, width, height);
-  set_background_none (xdisplay, GDK_WINDOW_XID (window));
-
-  return meta_frames_manage_window (ui->frames, meta_window, GDK_WINDOW_XID (window), window);
+  MetaUIFrame *frame = g_new0 (MetaUIFrame, 1);
+  frame->meta_window = meta_window;
+  frame->xwindow = meta_window ? meta_window->xwindow : None;
+  if (create_serial != NULL)
+    *create_serial = 0;
+  return frame;
 }
 
 void
-meta_ui_map_frame   (MetaUI *ui,
-                     Window  xwindow)
+meta_ui_move_resize_frame (MetaUI *ui,
+                           Window  frame,
+                           int     x,
+                           int     y,
+                           int     width,
+                           int     height)
 {
-  GdkWindow *window;
-  GdkDisplay *display;
-
-  display = gdk_x11_lookup_xdisplay (ui->xdisplay);
-  window = gdk_x11_window_lookup_for_display (display, xwindow);
+}
 
-  if (window)
-    gdk_window_show_unraised (window);
+void
+meta_ui_map_frame (MetaUI *ui,
+                   Window  xwindow)
+{
 }
 
 void
 meta_ui_unmap_frame (MetaUI *ui,
                      Window  xwindow)
 {
-  GdkWindow *window;
-  GdkDisplay *display;
-
-  display = gdk_x11_lookup_xdisplay (ui->xdisplay);
-  window = gdk_x11_window_lookup_for_display (display, xwindow);
-
-  if (window)
-    gdk_window_hide (window);
 }
 
 gboolean
 meta_ui_window_should_not_cause_focus (Display *xdisplay,
                                        Window   xwindow)
 {
-  GdkWindow *window;
-  GdkDisplay *display;
+  return FALSE;
+}
 
-  display = gdk_x11_lookup_xdisplay (xdisplay);
-  window = gdk_x11_window_lookup_for_display (display, xwindow);
+gboolean
+meta_ui_window_is_widget (MetaUI *ui,
+                          Window  xwindow)
+{
+  return FALSE;
+}
 
-  /* we shouldn't cause focus if we're an override redirect
-   * toplevel which is not foreign
-   */
-  if (window && gdk_window_get_window_type (window) == GDK_WINDOW_TEMP)
-    return TRUE;
-  else
-    return FALSE;
+gboolean
+meta_ui_window_is_dummy (MetaUI *ui,
+                         Window  xwindow)
+{
+  return FALSE;
 }
 
 void
-meta_ui_theme_get_frame_borders (MetaUI *ui,
-                                 MetaFrameType      type,
-                                 MetaFrameFlags     flags,
-                                 MetaFrameBorders  *borders)
+meta_ui_frame_unmanage (MetaUIFrame *frame)
 {
-  GdkDisplay *display;
-  GdkScreen *screen;
-  int text_height;
-  MetaStyleInfo *style_info = NULL;
-  PangoContext *context;
-  const PangoFontDescription *font_desc;
-  PangoFontDescription *free_font_desc = NULL;
-
-  display = gdk_x11_lookup_xdisplay (ui->xdisplay);
-  screen = gdk_display_get_default_screen (display);
+  if (frame != NULL)
+    g_free (frame);
+}
 
-  style_info = meta_theme_create_style_info (screen, NULL);
+void
+meta_ui_frame_set_title (MetaUIFrame *frame,
+                         const char  *title)
+{
+}
 
-  context = gtk_widget_get_pango_context (GTK_WIDGET (ui->frames));
-  font_desc = meta_prefs_get_titlebar_font ();
+void
+meta_ui_frame_update_style (MetaUIFrame *frame)
+{
+}
 
-  if (!font_desc)
-    {
-      free_font_desc = meta_style_info_create_font_desc (style_info);
-      font_desc = (const PangoFontDescription *) free_font_desc;
-    }
+void
+meta_ui_frame_get_borders (MetaUIFrame      *frame,
+                           MetaFrameBorders *borders)
+{
+  if (borders != NULL)
+    memset (borders, 0, sizeof (*borders));
+}
 
-  text_height = meta_pango_font_desc_get_text_height (font_desc, context);
+cairo_region_t *
+meta_ui_frame_get_bounds (MetaUIFrame *frame)
+{
+  return cairo_region_create ();
+}
 
-  meta_theme_get_frame_borders (meta_theme_get_default (),
-                                style_info, type, text_height, flags,
-                                borders);
+void
+meta_ui_frame_get_mask (MetaUIFrame           *frame,
+                        cairo_rectangle_int_t *rect)
+{
+  if (rect != NULL)
+    memset (rect, 0, sizeof (*rect));
+}
 
-  if (free_font_desc)
-    pango_font_description_free (free_font_desc);
+void
+meta_ui_frame_move_resize (MetaUIFrame *frame,
+                           int          x,
+                           int          y,
+                           int          width,
+                           int          height)
+{
+}
 
-  if (style_info != NULL)
-    meta_style_info_unref (style_info);
+void
+meta_ui_frame_queue_draw (MetaUIFrame *frame)
+{
 }
 
 gboolean
-meta_ui_window_is_widget (MetaUI *ui,
-                          Window  xwindow)
+meta_ui_frame_handle_event (MetaUIFrame        *frame,
+                            const ClutterEvent *event)
 {
-  GdkDisplay *display;
-  GdkWindow *window;
+  return FALSE;
+}
 
-  display = gdk_x11_lookup_xdisplay (ui->xdisplay);
-  window = gdk_x11_window_lookup_for_display (display, xwindow);
+/*
+ * meta/theme.h API: the metacity theme engine is gone, but the public
+ * symbols stay so libmuffin keeps its ABI surface for the GIR.
+ */
+struct _MetaTheme
+{
+  int unused;
+};
 
-  if (window)
-    {
-      void *user_data = NULL;
-      gdk_window_get_user_data (window, &user_data);
-      return user_data != NULL && user_data != ui->frames;
-    }
-  else
-    return FALSE;
+static MetaTheme default_theme = { 0 };
+
+MetaTheme *
+meta_theme_get_default (void)
+{
+  return &default_theme;
 }
 
-gboolean
-meta_ui_window_is_dummy (MetaUI *ui,
-                         Window  xwindow)
+MetaTheme *
+meta_theme_new (void)
+{
+  return g_new0 (MetaTheme, 1);
+}
+
+void
+meta_theme_free (MetaTheme *theme)
 {
-  GdkWindow *frames_window = gtk_widget_get_window (GTK_WIDGET (ui->frames));
-  return xwindow == gdk_x11_window_get_xid (frames_window);
+  if (theme != &default_theme)
+    g_free (theme);
 }
