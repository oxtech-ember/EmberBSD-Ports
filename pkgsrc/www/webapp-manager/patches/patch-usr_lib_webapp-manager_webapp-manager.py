$NetBSD$

Local: pkgsrc prefix and Ember Browser integration.

--- usr/lib/webapp-manager/webapp-manager.py
+++ usr/lib/webapp-manager/webapp-manager.py
@@ -21,13 +21,13 @@
 from gi.repository import Gtk, Gdk, Gio, XApp, GdkPixbuf, GLib
 
 #   3. Local application/library specific imports.
-from common import _async, idle, WebAppManager, download_favicon, ICONS_DIR, BROWSER_TYPE_FIREFOX, BROWSER_TYPE_FIREFOX_FLATPAK, BROWSER_TYPE_ZEN_FLATPAK, BROWSER_TYPE_FIREFOX_SNAP
+from common import _async, idle, WebAppManager, download_favicon, ICONS_DIR, BROWSER_TYPE_FIREFOX, BROWSER_TYPE_FIREFOX_FLATPAK, BROWSER_TYPE_ZEN_FLATPAK, BROWSER_TYPE_FIREFOX_SNAP, BROWSER_TYPE_EMBER, ember_webapp_validation
 
 setproctitle.setproctitle("webapp-manager")
 
 # i18n
 APP = 'webapp-manager'
-LOCALE_DIR = "/usr/share/locale"
+LOCALE_DIR = "@PREFIX@/share/locale"
 locale.bindtextdomain(APP, LOCALE_DIR)
 gettext.bindtextdomain(APP, LOCALE_DIR)
 gettext.textdomain(APP)
@@ -69,7 +69,7 @@
         self.icon_theme = Gtk.IconTheme.get_default()
 
         # Set the Glade file
-        gladefile = "/usr/share/webapp-manager/webapp-manager.ui"
+        gladefile = "@PREFIX@/share/webapp-manager/webapp-manager.ui"
         self.builder = Gtk.Builder()
         self.builder.set_translation_domain(APP)
         self.builder.add_from_file(gladefile)
@@ -94,7 +94,13 @@
         self.desc_entry = self.builder.get_object("desc_entry")
         self.url_entry = self.builder.get_object("url_entry")
         self.url_label = self.builder.get_object("url_label")
+        self.validation_label = Gtk.Label()
+        self.validation_label.set_line_wrap(True)
+        self.validation_label.set_max_width_chars(48)
+        self.validation_label.get_style_context().add_class("error")
+        self.url_label.get_parent().get_parent().pack_start(self.validation_label, False, False, 0)
         self.customparameters_entry = self.builder.get_object("customparameters_entry")
+        self.customparameters_label = self.builder.get_object("customparameters_label")
         self.isolated_switch = self.builder.get_object("isolated_switch")
         self.isolated_label = self.builder.get_object("isolated_label")
         self.navbar_switch = self.builder.get_object("navbar_switch")
@@ -226,7 +232,7 @@
         cell.set_property("surface", surface)
 
     def open_keyboard_shortcuts(self, widget):
-        gladefile = "/usr/share/webapp-manager/shortcuts.ui"
+        gladefile = "@PREFIX@/share/webapp-manager/shortcuts.ui"
         builder = Gtk.Builder()
         builder.set_translation_domain(APP)
         builder.add_from_file(gladefile)
@@ -289,7 +295,18 @@
             dialog.format_secondary_text(_("This Web App will be permanently lost."))
             dialog.show()
             if dialog.run() == Gtk.ResponseType.YES:
-                self.manager.delete_webbapp(self.selected_webapp)
+                try:
+                    self.manager.delete_webbapp(self.selected_webapp)
+                except RuntimeError as error:
+                    dialog.destroy()
+                    failure = Gtk.MessageDialog(transient_for=self.window,
+                                                message_type=Gtk.MessageType.ERROR,
+                                                buttons=Gtk.ButtonsType.CLOSE,
+                                                text=_("Unable to delete Web App"))
+                    failure.format_secondary_text(str(error))
+                    failure.run()
+                    failure.destroy()
+                    return
                 self.load_webapps()
             dialog.destroy()
 
@@ -297,7 +314,9 @@
         if webapp is not None:
             print("Running %s" % webapp.path)
             print("Executing %s" % webapp.exec)
-            subprocess.Popen(webapp.exec, shell=True)
+            app = Gio.DesktopAppInfo.new_from_filename(webapp.path)
+            if app is not None:
+                app.launch([], None)
 
     def on_run_button(self, widget):
         self.run_webapp(self.selected_webapp)
@@ -445,10 +464,23 @@
 
     def on_browser_changed(self, widget):
         self.show_hide_browser_widgets()
+        self.toggle_ok_sensitivity()
 
     def show_hide_browser_widgets(self):
         browser = self.browser_combo.get_model()[self.browser_combo.get_active()][BROWSER_OBJ]
-        if browser.browser_type in [BROWSER_TYPE_FIREFOX, BROWSER_TYPE_FIREFOX_FLATPAK, BROWSER_TYPE_FIREFOX_SNAP, BROWSER_TYPE_ZEN_FLATPAK]:
+        self.customparameters_entry.set_visible(browser.browser_type != BROWSER_TYPE_EMBER)
+        self.customparameters_label.set_visible(browser.browser_type != BROWSER_TYPE_EMBER)
+        if browser.browser_type == BROWSER_TYPE_EMBER:
+            self.customparameters_entry.hide()
+            self.customparameters_label.hide()
+            self.isolated_switch.set_active(True)
+            self.isolated_label.hide()
+            self.isolated_switch.hide()
+            self.navbar_label.hide()
+            self.navbar_switch.hide()
+            self.privatewindow_label.show()
+            self.privatewindow_switch.show()
+        elif browser.browser_type in [BROWSER_TYPE_FIREFOX, BROWSER_TYPE_FIREFOX_FLATPAK, BROWSER_TYPE_FIREFOX_SNAP, BROWSER_TYPE_ZEN_FLATPAK]:
             self.isolated_label.hide()
             self.isolated_switch.hide()
             self.navbar_label.show()
@@ -475,10 +507,13 @@
         self.guess_icon()
 
     def toggle_ok_sensitivity(self):
-        if self.name_entry.get_text() == "" or self.get_url() == "":
-            self.ok_button.set_sensitive(False)
-        else:
-            self.ok_button.set_sensitive(True)
+        browser = self.browser_combo.get_model()[self.browser_combo.get_active()][BROWSER_OBJ]
+        name = self.name_entry.get_text()
+        url = self.get_url()
+        reason = ember_webapp_validation(name, url) if browser.browser_type == BROWSER_TYPE_EMBER and (name or url) else ""
+        self.validation_label.set_text(reason)
+        self.validation_label.set_visible(bool(reason))
+        self.ok_button.set_sensitive(bool(name and url) and not reason)
 
     def guess_icon(self):
         url = self.get_url().lower()
