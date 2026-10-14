$NetBSD$

Pango defines the PangoRenderer autoptr cleanup itself in current
releases; the local definition is a redefinition. Origin: EmberBSD (AI-assisted).

--- clutter/clutter/pango/clutter-pango-private.h	2026-09-15 17:26:39.000000000 +0300
+++ clutter/clutter/pango/clutter-pango-private.h	2026-10-14 11:12:54.872139438 +0300
@@ -79,7 +79,9 @@
                           ClutterColorState *color_state,
                           ClutterColorState *target_color_state);
 
+#if !PANGO_VERSION_CHECK(1, 50, 0)
 G_DEFINE_AUTOPTR_CLEANUP_FUNC (PangoRenderer, g_object_unref)
+#endif
 
 static inline PangoDirection
 clutter_text_direction_to_pango_direction (ClutterTextDirection dir)
