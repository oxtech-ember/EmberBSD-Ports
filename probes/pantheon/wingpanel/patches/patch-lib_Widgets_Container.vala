$NetBSD$

EmberBSD GTK4 port: widget APIs moved in GTK4 (add->append child, style
classes via widgets, paintable icons); take the upstream gtk4-branch
rewrite. Origin: EmberBSD (AI-assisted).

--- lib/Widgets/Container.vala	2025-12-03 19:15:29.000000000 +0300
+++ lib/Widgets/Container.vala	2023-02-02 15:09:09.000000000 +0300
@@ -18,21 +18,4 @@
  */
 
 [Version (deprecated = true, deprecated_since = "3.0.0", replacement = "Gtk.ModelButton")]
-public class Wingpanel.Widgets.Container : Gtk.Button {
-    public Gtk.Grid content_widget { owned get; construct; }
-
-    public extern Gtk.Grid get_content_widget ();
-
-    public Container () {}
-
-    construct {
-        content_widget = new Gtk.Grid ();
-        content_widget.hexpand = true;
-        add (content_widget);
-
-        var style_context = this.get_style_context ();
-        style_context.add_class (Gtk.STYLE_CLASS_MENUITEM);
-        style_context.remove_class (Gtk.STYLE_CLASS_BUTTON);
-        style_context.remove_class ("text-button");
-    }
-}
+public class Wingpanel.Widgets.Container : Gtk.Button {}
