$NetBSD$

EmberBSD GTK4 port: widget APIs moved in GTK4 (add->append child, style
classes via widgets, paintable icons); take the upstream gtk4-branch
rewrite. Origin: EmberBSD (AI-assisted).

--- lib/Widgets/OverlayIcon.vala	2025-12-03 19:15:29.000000000 +0300
+++ lib/Widgets/OverlayIcon.vala	2023-02-02 15:09:09.000000000 +0300
@@ -17,68 +17,5 @@
  * Boston, MA 02110-1301 USA.
  */
 
-public class Wingpanel.Widgets.OverlayIcon : Gtk.Overlay {
-    private Gtk.Image main_image;
-    private Gtk.Image overlay_image;
-
-    public OverlayIcon (string icon_name) {
-        set_main_icon_name (icon_name);
-    }
-
-    public OverlayIcon.from_pixbuf (Gdk.Pixbuf pixbuf) {
-        set_main_pixbuf (pixbuf);
-    }
-
-    construct {
-        main_image = new Gtk.Image ();
-        main_image.icon_size = 24;
-        main_image.pixel_size = 24;
-
-        overlay_image = new Gtk.Image ();
-        overlay_image.icon_size = 24;
-        overlay_image.pixel_size = 24;
-
-        add (main_image);
-        add_overlay (overlay_image);
-    }
-
-    public void set_main_pixbuf (Gdk.Pixbuf? pixbuf) {
-        main_image.set_from_pixbuf (pixbuf);
-    }
-
-    public Gdk.Pixbuf? get_main_pixbuf () {
-        return main_image.get_pixbuf ();
-    }
-
-    public void set_overlay_pixbuf (Gdk.Pixbuf? pixbuf) {
-        overlay_image.set_from_pixbuf (pixbuf);
-    }
-
-    public Gdk.Pixbuf? get_overlay_pixbuf () {
-        return overlay_image.get_pixbuf ();
-    }
-
-    public void set_main_icon_name (string icon_name) {
-        main_image.icon_name = icon_name;
-    }
-
-    public string get_main_icon_name () {
-        return main_image.icon_name;
-    }
-
-    public void set_overlay_icon_name (string icon_name) {
-        overlay_image.icon_name = icon_name;
-    }
-
-    public string get_overlay_icon_name () {
-        return overlay_image.icon_name;
-    }
-
-    public Gtk.Image get_main_image () {
-        return main_image;
-    }
-
-    public Gtk.Image get_overlay_image () {
-        return overlay_image;
-    }
-}
+[Version (deprecated = true, deprecated_since = "3.0.0", replacement = "Gtk.Overlay")]
+public class Wingpanel.Widgets.OverlayIcon : Gtk.Box { }
\ No newline at end of file
