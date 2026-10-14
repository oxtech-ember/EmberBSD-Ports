$NetBSD$

EmberBSD GTK4 port: Gtk.Bin is gone in GTK4; the widget collapses to a
Box wrapper (matching the upstream gtk4 branch). Origin: EmberBSD (AI-assisted).

--- lib/Widgets/Switch.vala.orig	2026-10-14 20:52:06.012492957 +0300
+++ lib/Widgets/Switch.vala	2026-10-14 20:52:06.014749002 +0300
@@ -18,63 +18,4 @@
  */
 
 [Version (deprecated = true, deprecated_since = "3.0.0", replacement = "Granite.SwitchModelButton")]
-public class Wingpanel.Widgets.Switch : Gtk.Bin {
-    public bool active { get; set; }
-    public string caption { owned get; set; }
-
-    private Gtk.Label button_label;
-    private Gtk.Switch button_switch;
-
-    public Switch (string caption, bool active = false) {
-        Object (caption: caption, active: active);
-    }
-
-    public Switch.with_mnemonic (string caption, bool active = false) {
-        Object (caption: caption, active: active);
-        button_label.set_text_with_mnemonic (caption);
-        button_label.set_mnemonic_widget (this);
-    }
-
-    construct {
-        button_switch = new Gtk.Switch ();
-        button_switch.active = active;
-        button_switch.halign = Gtk.Align.END;
-        button_switch.hexpand = true;
-        button_switch.valign = Gtk.Align.CENTER;
-
-        button_label = new Gtk.Label (null);
-        button_label.halign = Gtk.Align.START;
-
-        var grid = new Gtk.Grid ();
-        grid.column_spacing = 12;
-        grid.attach (button_label, 0, 0);
-        grid.attach (button_switch, 1, 0);
-
-        var modelbutton = new Gtk.ModelButton ();
-        modelbutton.get_child ().destroy ();
-        modelbutton.add (grid);
-
-        add (modelbutton);
-
-        modelbutton.button_release_event.connect (() => {
-            toggle_switch ();
-            // Stop modelbutton from closing the popover
-            return Gdk.EVENT_STOP;
-        });
-
-        bind_property ("active", button_switch, "active", GLib.BindingFlags.SYNC_CREATE | GLib.BindingFlags.BIDIRECTIONAL);
-        bind_property ("caption", button_label, "label", GLib.BindingFlags.SYNC_CREATE | GLib.BindingFlags.BIDIRECTIONAL);
-    }
-
-    public new Gtk.Label get_label () {
-        return button_label;
-    }
-
-    public Gtk.Switch get_switch () {
-        return button_switch;
-    }
-
-    public void toggle_switch () {
-        button_switch.activate ();
-    }
-}
+public class Wingpanel.Widgets.Switch : Gtk.Box {}
