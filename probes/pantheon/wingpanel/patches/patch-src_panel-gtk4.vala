$NetBSD$

EmberBSD GTK4 port: GestureMultiPress is GestureClick in GTK4, Gtk.EventBox
is gone, Gdk.Screen is gone (providers attach to the display, monitors come
from Gdk.Display.get_monitors), size_allocate/resize/show_all/app_paintable
and the skip pager/taskbar hints are gone, rgba visual selection is
implicit, EventControllerKey takes no widget, popovers take a parent
instead of a relative-to widget and use autohide, containers append
children, seat ungrab is gone, the X11 window id comes from a top-level
gdk_x11_surface_get_xid extern, and the wayland surface accessor lives on
Gdk.Wayland.Surface. Origin: EmberBSD (AI-assisted).

--- src/Services/PopoverManager.vala	2025-12-03 19:15:29.000000000 +0300
+++ PopoverManager.vala	2026-10-14 22:43:11.182899567 +0300
@@ -20,7 +20,7 @@
 public class Wingpanel.Services.PopoverManager : Object {
     private unowned Wingpanel.PanelWindow? owner;
 
-    private Gtk.GestureMultiPress owner_gesture_controller;
+    private Gtk.GestureClick owner_gesture_controller;
 
     private Gee.HashMap<string, Wingpanel.Widgets.IndicatorEntry> registered_indicators;
     private Wingpanel.Widgets.IndicatorPopover popover;
@@ -51,15 +51,14 @@
 
             if (_current_indicator != null) {
                 popover.set_content (_current_indicator.indicator_widget);
-                popover.relative_to = _current_indicator;
+                popover.set_parent (_current_indicator);
                 update_has_tooltip (_current_indicator.display_widget, false);
                 owner.set_expanded (true);
                 owner.present ();
                 popover.popup ();
-                popover.show_all ();
                 _current_indicator.base_indicator.opened ();
             } else {
-                update_has_tooltip (((Wingpanel.Widgets.IndicatorEntry)popover.get_relative_to ()).display_widget);
+                update_has_tooltip (_current_indicator.display_widget);
                 popover.popdown ();
             }
         }
@@ -85,13 +84,9 @@
             });
         });
 
-        owner_gesture_controller = new Gtk.GestureMultiPress (owner) {
-            window = owner.get_window ()
-        };
+        owner_gesture_controller = new Gtk.GestureClick ();
+        ((Gtk.Widget) owner).add_controller (owner_gesture_controller);
         owner_gesture_controller.pressed.connect (() => current_indicator = null);
-
-        //Replace with EventController propagation limit SAME_NATIVE in GTK 4
-        owner.realize.connect (() => owner_gesture_controller.window = owner.get_window ());
     }
 
     public void set_popover_visible (string code_name, bool visible) {
--- src/Widgets/IndicatorEntry.vala	2025-12-03 19:15:29.000000000 +0300
+++ IndicatorEntry.vala	2026-10-14 22:48:01.204510414 +0300
@@ -17,13 +17,16 @@
  * Boston, MA 02110-1301 USA.
  */
 
-public class Wingpanel.Widgets.IndicatorEntry : Gtk.EventBox {
+public class Wingpanel.Widgets.IndicatorEntry : Gtk.Box {
     public Indicator base_indicator { get; construct; }
     public Services.PopoverManager popover_manager { get; construct; }
 
     public IndicatorBar? indicator_bar;
     public Gtk.Widget display_widget { get; private set; }
 
+    private Gtk.EventControllerScroll scroll_controller;
+    private Gtk.GestureClick button_controller;
+
     private Gtk.Widget _indicator_widget = null;
     public unowned Gtk.Widget indicator_widget {
         get {
@@ -37,7 +40,7 @@
 
     private Gtk.Revealer revealer;
 
-    private Gtk.GestureMultiPress gesture_controller;
+    private Gtk.GestureClick gesture_controller;
     private Gtk.EventControllerMotion motion_controller;
 
     public IndicatorEntry (Indicator base_indicator, Services.PopoverManager popover_manager) {
@@ -62,7 +65,7 @@
         };
         revealer.get_style_context ().add_class ("composited-indicator");
 
-        add (revealer);
+        append (revealer);
 
         if (base_indicator.visible) {
             popover_manager.register_indicator (this);
@@ -92,24 +95,19 @@
             }
         });
 
-        add_events (Gdk.EventMask.SCROLL_MASK);
-        add_events (Gdk.EventMask.SMOOTH_SCROLL_MASK);
-
-        scroll_event.connect ((e) => {
-            return display_widget.scroll_event (e);
-        });
-
-        button_press_event.connect ((e) => display_widget.button_press_event (e));
-
-        gesture_controller = new Gtk.GestureMultiPress (this);
+        /* GTK4: indicator modules draw their own input through controllers;
+         * the GTK3 widget event signals are gone. Origin: EmberBSD. */
+        gesture_controller = new Gtk.GestureClick ();
         gesture_controller.pressed.connect (() => {
             popover_manager.current_indicator = this;
             gesture_controller.set_state (CLAIMED);
         });
+        add_controller (gesture_controller);
 
-        motion_controller = new Gtk.EventControllerMotion (this) {
+        motion_controller = new Gtk.EventControllerMotion () {
             propagation_phase = CAPTURE
         };
+        add_controller (motion_controller);
 
         motion_controller.enter.connect (() => {
             // If something is open and it's not us, open us. This implements the scrubbing behavior
--- src/Widgets/Panel.vala	2025-12-03 19:15:29.000000000 +0300
+++ Panel.vala	2026-10-14 22:51:42.397528175 +0300
@@ -17,7 +17,7 @@
  * Boston, MA 02110-1301 USA.
  */
 
-public class Wingpanel.Widgets.Panel : Gtk.EventBox {
+public class Wingpanel.Widgets.Panel : Gtk.Box {
     private static Settings panel_settings = new Settings ("io.elementary.desktop.wingpanel");
 
     public Services.PopoverManager popover_manager { get; construct; }
@@ -29,7 +29,7 @@
     private unowned Gtk.StyleContext style_context;
     private Gtk.CssProvider? style_provider = null;
 
-    private Gtk.GestureMultiPress gesture_controller;
+    private Gtk.GestureClick gesture_controller;
     private Gtk.EventControllerScroll scroll_controller;
     private double current_scroll_delta = 0;
 
@@ -58,11 +58,13 @@
         };
 
         var box = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 0);
-        box.pack_start (left_menubar);
-        box.set_center_widget (center_menubar);
-        box.pack_end (right_menubar);
+        center_menubar.hexpand = true;
+        center_menubar.halign = Gtk.Align.CENTER;
+        box.append (left_menubar);
+        box.append (center_menubar);
+        box.append (right_menubar);
 
-        add (box);
+        append (box);
 
         unowned IndicatorManager indicator_manager = IndicatorManager.get_default ();
         indicator_manager.indicator_added.connect (add_indicator);
@@ -78,18 +80,20 @@
 
         Services.BackgroundManager.get_default ().background_state_changed.connect (update_background);
 
-        gesture_controller = new Gtk.GestureMultiPress (this);
+        gesture_controller = new Gtk.GestureClick ();
+        add_controller (gesture_controller);
         gesture_controller.pressed.connect ((n_press, x, y) => {
             begin_drag (x, y);
             gesture_controller.set_state (CLAIMED);
             gesture_controller.reset ();
         });
 
-        scroll_controller = new Gtk.EventControllerScroll (this, BOTH_AXES);
+        scroll_controller = new Gtk.EventControllerScroll (Gtk.EventControllerScrollFlags.BOTH_AXES);
+        add_controller (scroll_controller);
         scroll_controller.scroll_end.connect (() => current_scroll_delta = 0);
         scroll_controller.scroll.connect ((dx, dy) => {
             if (!panel_settings.get_boolean ("scroll-to-switch-workspaces")) {
-                return;
+                return true;
             }
 
             if (current_scroll_delta == 0) {
@@ -101,17 +105,19 @@
             if (current_scroll_delta.abs () > 1) { // Balance between reactive and ignoring misinput
                 current_scroll_delta = 0;
             }
+
+            return true;
         });
     }
 
     private void begin_drag (double x, double y) {
-        var window = get_window ();
+        var window = ((Gtk.Native) this).get_surface ();
         if (window == null) {
             return;
         }
 
-        window.get_display ().get_default_seat ().ungrab ();
-
+        /* GTK4: implicit grabs are gone; the drag begins over the gala
+         * background window without an explicit seat ungrab. */
         popover_manager.close ();
 
         var background_manager = Services.BackgroundManager.get_default ();
@@ -250,11 +256,11 @@
         switch (indicator.code_name) {
             case Indicator.APP_LAUNCHER:
                 indicator_entry.set_transition_type (Gtk.RevealerTransitionType.SLIDE_RIGHT);
-                left_menubar.add (indicator_entry);
+                left_menubar.append (indicator_entry);
                 break;
             case Indicator.DATETIME:
                 indicator_entry.set_transition_type (Gtk.RevealerTransitionType.SLIDE_DOWN);
-                center_menubar.add (indicator_entry);
+                center_menubar.append (indicator_entry);
                 break;
             default:
                 indicator_entry.set_transition_type (Gtk.RevealerTransitionType.SLIDE_LEFT);
@@ -262,7 +268,6 @@
                 break;
         }
 
-        indicator_entry.show_all ();
     }
 
     private void remove_indicator (Indicator indicator) {
@@ -274,8 +279,8 @@
     private void update_background (Services.BackgroundState state, uint animation_duration) {
         if (style_provider == null) {
             style_provider = new Gtk.CssProvider ();
-            Gtk.StyleContext.add_provider_for_screen (
-                Gdk.Screen.get_default (),
+            Gtk.StyleContext.add_provider_for_display (
+                Gdk.Display.get_default (),
                 style_provider,
                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
             );
@@ -288,7 +293,7 @@
         """.printf (animation_duration);
 
         try {
-            style_provider.load_from_data (css, css.length);
+            style_provider.load_from_data (css.data);
         } catch (Error e) {
             warning ("Parsing own style configuration failed: %s", e.message);
         }
--- src/Widgets/IndicatorPopover.vala	2025-12-03 19:15:29.000000000 +0300
+++ IndicatorPopover.vala	2026-10-14 22:43:11.183959695 +0300
@@ -24,7 +24,7 @@
 
     construct {
         width_request = 256;
-        modal = false;
+        autohide = false;
         name = name + "/popover";
         position = Gtk.PositionType.BOTTOM;
 
@@ -47,7 +47,7 @@
         }
 
         if (content != null) {
-            container.add (content);
+            container.append (content);
             widget = content;
         }
     }
--- src/Widgets/IndicatorBar.vala	2025-12-03 19:15:29.000000000 +0300
+++ IndicatorBar.vala	2026-10-14 22:36:54.976619289 +0300
@@ -46,12 +46,38 @@
             }
 
             if (item.get_parent () != this) {
-                add (item);
-                reorder_child (item, index);
+                append (item);
+                /* GTK4: manual reorder of the appended child. */
+                unowned Gtk.Widget? next = null;
+                unowned Gtk.Widget? walk = get_first_child ();
+                while (walk != null) {
+                    if (walk == item) {
+                        break;
+                    }
+                    if (walk is IndicatorEntry) {
+                        next = walk;
+                    }
+                    walk = walk.get_next_sibling ();
+                }
+                if (next != null) {
+                    if (next != null) {
+                        insert_child_after (item, next);
+                    }
+                }
             }
         }
     }
 
+    public GLib.List<Gtk.Widget> get_children () {
+        var list = new GLib.List<Gtk.Widget> ();
+        unowned Gtk.Widget? walk = get_first_child ();
+        while (walk != null) {
+            list.append (walk);
+            walk = walk.get_next_sibling ();
+        }
+        return list;
+    }
+
     public void remove_indicator (Indicator indicator) {
         foreach (var entry in sorted_items) {
             if (entry.base_indicator.code_name == indicator.code_name) {
--- src/PanelWindow.vala	2025-12-03 19:15:29.000000000 +0300
+++ PanelWindow.vala	2026-10-14 22:57:55.659202553 +0300
@@ -17,6 +17,9 @@
  * Boston, MA 02110-1301 USA.
  */
 
+[CCode (cname = "gdk_x11_surface_get_xid")]
+extern size_t gdk_x11_surface_get_xid (Gdk.Surface surface);
+
 public class Wingpanel.PanelWindow : Gtk.Window {
     public Services.PopoverManager popover_manager;
 
@@ -34,23 +37,19 @@
     public PanelWindow (Gtk.Application application) {
         Object (
             application: application,
-            app_paintable: true,
             decorated: false,
             resizable: false,
-            skip_pager_hint: true,
-            skip_taskbar_hint: true,
             vexpand: false
         );
 
         var app_provider = new Gtk.CssProvider ();
         app_provider.load_from_resource ("io/elementary/wingpanel/Application.css");
-        Gtk.StyleContext.add_provider_for_screen (Gdk.Screen.get_default (), app_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION);
+        Gtk.StyleContext.add_provider_for_display (Gdk.Display.get_default (), app_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION);
 
-        this.screen.size_changed.connect (update_panel_dimensions);
-        this.screen.monitors_changed.connect (update_panel_dimensions);
-        this.screen_changed.connect (update_visual);
+        var default_display = Gdk.Display.get_default ();
+        default_display.get_monitors ().items_changed.connect (update_panel_dimensions);
+        notify["default-width"].connect (update_panel_dimensions);
 
-        update_visual ();
 
         popover_manager = new Services.PopoverManager (this);
 
@@ -76,10 +75,10 @@
 
         child = revealer;
 
-        key_controller = new Gtk.EventControllerKey (this);
+        key_controller = new Gtk.EventControllerKey ();
         key_controller.key_pressed.connect (on_key_pressed);
 
-        panel.size_allocate.connect (update_panel_dimensions);
+        panel.notify["allocated-height"].connect (update_panel_dimensions);
 
         notify["scale-factor"].connect (on_scale_changed);
     }
@@ -100,7 +99,7 @@
         panel_height = panel.get_allocated_height ();
 
         // We just use our monitor because Gala makes sure we are always on the primary one
-        var monitor_dimensions = get_display ().get_monitor_at_window (get_window ()).get_geometry ();
+        var monitor_dimensions = get_display ().get_monitor_at_surface (get_surface ()).get_geometry ();
 
         if (!Services.DisplayConfig.is_logical_layout () && Gdk.Display.get_default () is Gdk.Wayland.Display) {
             monitor_dimensions.width /= get_scale_factor ();
@@ -115,16 +114,6 @@
         this.set_size_request (monitor_width, (popover_manager.current_indicator != null ? monitor_height : -1));
     }
 
-    private void update_visual () {
-        var visual = this.screen.get_rgba_visual ();
-
-        if (visual == null) {
-            warning ("Compositing not available, things will Look Bad (TM)");
-        } else {
-            this.set_visual (visual);
-        }
-    }
-
     private bool on_key_pressed (uint keyval, uint keycode, Gdk.ModifierType state) {
         if (keyval == Gdk.Key.Escape) {
             popover_manager.close ();
@@ -148,7 +137,7 @@
 
             this.expanded = false;
             this.set_size_request (monitor_width, -1);
-            this.resize (monitor_width, 1);
+            set_size_request (monitor_width, 1);
         }
     }
 
@@ -183,7 +172,7 @@
         if (display is Gdk.X11.Display) {
             unowned var xdisplay = ((Gdk.X11.Display) display).get_xdisplay ();
 
-            var window = ((Gdk.X11.Window) get_window ()).get_xid ();
+            var window = gdk_x11_surface_get_xid ((Gdk.Surface) get_surface ());
 
             var prop = xdisplay.intern_atom ("_MUTTER_HINTS", false);
 
@@ -196,9 +185,9 @@
     public void registry_handle_global (Wl.Registry wl_registry, uint32 name, string @interface, uint32 version) {
         if (@interface == "io_elementary_pantheon_shell_v1") {
             desktop_shell = wl_registry.bind<Pantheon.Desktop.Shell> (name, ref Pantheon.Desktop.Shell.iface, uint32.min (version, 1));
-            unowned var window = get_window ();
-            if (window is Gdk.Wayland.Window) {
-                unowned var wl_surface = ((Gdk.Wayland.Window) window).get_wl_surface ();
+            unowned var window = get_surface ();
+            if (window is Gdk.Wayland.Surface) {
+                unowned var wl_surface = ((Gdk.Wayland.Surface) window).get_wl_surface ();
                 desktop_panel = desktop_shell.get_panel (wl_surface);
                 desktop_panel.set_anchor (TOP);
                 desktop_panel.set_hide_mode (NEVER);
--- src/Application.vala	2025-12-03 19:15:29.000000000 +0300
+++ Application.vala	2026-10-14 22:20:49.453895630 +0300
@@ -113,7 +113,6 @@
         base.startup ();
 
         panel_window = new PanelWindow (this);
-        panel_window.show_all ();
 
         register_actions ();
     }
