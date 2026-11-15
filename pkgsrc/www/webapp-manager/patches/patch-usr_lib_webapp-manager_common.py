$NetBSD$

Local: pkgsrc prefix, GLib desktop string handling and Ember Browser integration.

--- usr/lib/webapp-manager/common.py
+++ usr/lib/webapp-manager/common.py
@@ -9,6 +9,7 @@
 from random import choice
 import shutil
 import string
+import secrets
 import sys
 import tempfile
 import urllib.error
@@ -19,7 +20,7 @@
 from typing import Optional
 
 #   2. Related third party imports.
-from gi.repository import GObject
+from gi.repository import GObject, GLib
 import PIL.Image
 import requests
 # Note: BeautifulSoup is an optional import supporting another way of getting a website's favicons.
@@ -42,7 +43,7 @@
 
 # i18n
 APP = 'webapp-manager'
-LOCALE_DIR = "/usr/share/locale"
+LOCALE_DIR = "@PREFIX@/share/locale"
 locale.bindtextdomain(APP, LOCALE_DIR)
 gettext.bindtextdomain(APP, LOCALE_DIR)
 gettext.textdomain(APP)
@@ -63,14 +64,44 @@
 FALKON_PROFILES_DIR = os.path.join(ICE_DIR, "falkon")
 ZEN_FLATPAK_PROFILES_DIR = os.path.expanduser("~/.var/app/app.zen_browser.zen/data/ice/zen/")
 ICONS_DIR = os.path.join(ICE_DIR, "icons")
-BROWSER_TYPE_FIREFOX, BROWSER_TYPE_FIREFOX_FLATPAK, BROWSER_TYPE_FIREFOX_SNAP, BROWSER_TYPE_LIBREWOLF_FLATPAK, BROWSER_TYPE_WATERFOX_FLATPAK, BROWSER_TYPE_FLOORP_FLATPAK, BROWSER_TYPE_CHROMIUM, BROWSER_TYPE_EPIPHANY, BROWSER_TYPE_FALKON, BROWSER_TYPE_ZEN_FLATPAK = range(10)
+BROWSER_TYPE_FIREFOX, BROWSER_TYPE_FIREFOX_FLATPAK, BROWSER_TYPE_FIREFOX_SNAP, BROWSER_TYPE_LIBREWOLF_FLATPAK, BROWSER_TYPE_WATERFOX_FLATPAK, BROWSER_TYPE_FLOORP_FLATPAK, BROWSER_TYPE_CHROMIUM, BROWSER_TYPE_EPIPHANY, BROWSER_TYPE_FALKON, BROWSER_TYPE_ZEN_FLATPAK, BROWSER_TYPE_EMBER = range(11)
+
+def ember_webapp_validation(name, url):
+    """Match Ember Browser's webapp argv restrictions before saving."""
+    if not name.strip() or len(name) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in name):
+        return _("Enter a name of at most 200 characters without control characters.")
+    if any(ord(c) <= 32 or ord(c) == 127 for c in url):
+        return _("Enter an HTTP or HTTPS address without spaces or credentials.")
+    try:
+        parsed = urllib.parse.urlsplit(url)
+        valid = (parsed.scheme in ("http", "https") and parsed.hostname and
+                 not parsed.username and not parsed.password)
+        if parsed.port is not None and not 0 <= parsed.port <= 65535:
+            valid = False
+    except ValueError:
+        valid = False
+    if not valid:
+        return _("Enter an HTTP or HTTPS address without spaces or credentials.")
+    return ""
+
+def desktop_string(value):
+    key = GLib.KeyFile()
+    key.set_string("Desktop Entry", "Value", value)
+    return key.get_value("Desktop Entry", "Value")
+
+
+def desktop_unstring(value):
+    key = GLib.KeyFile()
+    key.set_value("Desktop Entry", "Value", value)
+    return key.get_string("Desktop Entry", "Value")
+
 
 class Browser:
 
     def __init__(self, browser_type, name, exec_path, test_path):
         self.browser_type = browser_type
         self.name = name
-        self.exec_path = exec_path
+        self.exec_path = test_path if test_path.startswith("@PREFIX@/bin/") else exec_path
         self.test_path = test_path
 
 # This is a data structure representing
@@ -96,23 +127,26 @@
         is_webapp = False
         with open(path) as desktop_file:
             for line in desktop_file:
-                line = line.strip()
+                line = line.lstrip().rstrip("\r\n")
 
                 # Identify if the app is a webapp
                 if "StartupWMClass=WebApp" in line or "StartupWMClass=Chromium" in line or "StartupWMClass=ICE-SSB" in line:
                     is_webapp = True
                     continue
 
-                if "Name=" in line:
-                    self.name = line.replace("Name=", "")
-                    continue
-
-                if "Comment=" in line:
-                    self.desc = line.replace("Comment=", "")
+                if line.startswith("Name="):
+                    self.name = desktop_unstring(line[len("Name="):])
+                    continue
+
+                if line.startswith("Comment="):
+                    self.desc = desktop_unstring(line[len("Comment="):])
                     if self.desc == _("Web App"):
                         self.desc = ""
                     continue
 
+                # Preserve exact Name/Comment strings while retaining upstream
+                # whitespace normalization for the remaining metadata.
+                line = line.strip()
                 if "Icon=" in line:
                     self.icon = line.replace("Icon=", "")
                     continue
@@ -182,69 +216,70 @@
     @staticmethod
     def get_supported_browsers():
         # type, name, exec, test
-        return [Browser(BROWSER_TYPE_FIREFOX, "Firefox", "firefox", "/usr/bin/firefox"),
-                Browser(BROWSER_TYPE_FIREFOX, "Firefox Developer Edition", "firefox-developer-edition", "/usr/bin/firefox-developer-edition"),
-                Browser(BROWSER_TYPE_FIREFOX, "Firefox Developer Edition", "firefox-developer", "/usr/bin/firefox-developer"),
-                Browser(BROWSER_TYPE_FIREFOX, "Firefox Developer Edition", "firefox-devedition", "/usr/bin/firefox-devedition"),
-                Browser(BROWSER_TYPE_FIREFOX, "Firefox Nightly", "firefox-nightly", "/usr/bin/firefox-nightly"),
-                Browser(BROWSER_TYPE_FIREFOX, "Firefox Extended Support Release", "firefox-esr", "/usr/bin/firefox-esr"),
+        return [Browser(BROWSER_TYPE_EMBER, "Ember Browser", "@PREFIX@/bin/ember-browser", "@PREFIX@/bin/ember-browser"),
+                Browser(BROWSER_TYPE_FIREFOX, "Firefox", "firefox", "@PREFIX@/bin/firefox"),
+                Browser(BROWSER_TYPE_FIREFOX, "Firefox Developer Edition", "firefox-developer-edition", "@PREFIX@/bin/firefox-developer-edition"),
+                Browser(BROWSER_TYPE_FIREFOX, "Firefox Developer Edition", "firefox-developer", "@PREFIX@/bin/firefox-developer"),
+                Browser(BROWSER_TYPE_FIREFOX, "Firefox Developer Edition", "firefox-devedition", "@PREFIX@/bin/firefox-devedition"),
+                Browser(BROWSER_TYPE_FIREFOX, "Firefox Nightly", "firefox-nightly", "@PREFIX@/bin/firefox-nightly"),
+                Browser(BROWSER_TYPE_FIREFOX, "Firefox Extended Support Release", "firefox-esr", "@PREFIX@/bin/firefox-esr"),
                 Browser(BROWSER_TYPE_FIREFOX_FLATPAK, "Firefox (Flatpak)", "/var/lib/flatpak/exports/bin/org.mozilla.firefox", "/var/lib/flatpak/exports/bin/org.mozilla.firefox"),
                 Browser(BROWSER_TYPE_FIREFOX_FLATPAK, "Firefox (Flatpak)", ".local/share/flatpak/exports/bin/org.mozilla.firefox", ".local/share/flatpak/exports/bin/org.mozilla.firefox"),
                 Browser(BROWSER_TYPE_ZEN_FLATPAK, "Zen (Flatpak)", "/var/lib/flatpak/exports/bin/app.zen_browser.zen", "/var/lib/flatpak/exports/bin/app.zen_browser.zen"),
                 Browser(BROWSER_TYPE_ZEN_FLATPAK, "Zen (Flatpak)", ".local/share/flatpak/exports/bin/app.zen_browser.zen", ".local/share/flatpak/exports/bin/app.zen_browser.zen"),
-                Browser(BROWSER_TYPE_FIREFOX, "Zen Browser", "zen-browser", "/usr/bin/zen-browser"),
+                Browser(BROWSER_TYPE_FIREFOX, "Zen Browser", "zen-browser", "@PREFIX@/bin/zen-browser"),
                 Browser(BROWSER_TYPE_FIREFOX_SNAP, "Firefox (Snap)", "/snap/bin/firefox", "/snap/bin/firefox"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Brave", "brave", "/usr/bin/brave"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Brave Browser", "brave-browser", "/usr/bin/brave-browser"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Brave (Bin)", "brave-bin", "/usr/bin/brave-bin"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Brave Origin", "brave-origin", "/usr/bin/brave-origin"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Chrome", "google-chrome-stable", "/usr/bin/google-chrome-stable"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Chrome (Beta)", "google-chrome-beta", "/usr/bin/google-chrome-beta"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Brave", "brave", "@PREFIX@/bin/brave"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Brave Browser", "brave-browser", "@PREFIX@/bin/brave-browser"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Brave (Bin)", "brave-bin", "@PREFIX@/bin/brave-bin"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Brave Origin", "brave-origin", "@PREFIX@/bin/brave-origin"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Chrome", "google-chrome-stable", "@PREFIX@/bin/google-chrome-stable"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Chrome (Beta)", "google-chrome-beta", "@PREFIX@/bin/google-chrome-beta"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Chrome (Flatpak)", "/var/lib/flatpak/exports/bin/com.google.Chrome", "/var/lib/flatpak/exports/bin/com.google.Chrome"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Chrome (Flatpak)", ".local/share/flatpak/exports/bin/com.google.Chrome", ".local/share/flatpak/exports/bin/com.google.Chrome"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Chromium", "chromium", "/usr/bin/chromium"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Chromium (chromium-browser)", "chromium-browser", "/usr/bin/chromium-browser"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Chromium", "chromium", "@PREFIX@/bin/chromium"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Chromium (chromium-browser)", "chromium-browser", "@PREFIX@/bin/chromium-browser"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Chromium (Snap)", "chromium", "/snap/bin/chromium"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Chromium (Bin)", "chromium-bin", "/usr/bin/chromium-bin-browser"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Helium", "helium", "/usr/bin/helium"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Ungoogled Chromium", "ungoogled-chromium", "/usr/bin/ungoogled-chromium"),
-                Browser(BROWSER_TYPE_EPIPHANY, "Epiphany", "epiphany", "/usr/bin/epiphany"),
-                Browser(BROWSER_TYPE_FIREFOX,  "LibreWolf", "librewolf", "/usr/bin/librewolf"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Chromium (Bin)", "chromium-bin", "@PREFIX@/bin/chromium-bin-browser"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Helium", "helium", "@PREFIX@/bin/helium"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Ungoogled Chromium", "ungoogled-chromium", "@PREFIX@/bin/ungoogled-chromium"),
+                Browser(BROWSER_TYPE_EPIPHANY, "Epiphany", "epiphany", "@PREFIX@/bin/epiphany"),
+                Browser(BROWSER_TYPE_FIREFOX,  "LibreWolf", "librewolf", "@PREFIX@/bin/librewolf"),
                 Browser(BROWSER_TYPE_LIBREWOLF_FLATPAK,  "LibreWolf (Flatpak)", "/var/lib/flatpak/exports/bin/io.gitlab.librewolf-community", "/var/lib/flatpak/exports/bin/io.gitlab.librewolf-community"),
                 Browser(BROWSER_TYPE_LIBREWOLF_FLATPAK,  "LibreWolf (Flatpak)", ".local/share/flatpak/exports/bin/io.gitlab.librewolf-community", ".local/share/flatpak/exports/bin/io.gitlab.librewolf-community"),
-                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox", "waterfox", "/usr/bin/waterfox"),
-                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox Current", "waterfox-current", "/usr/bin/waterfox-current"),
-                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox Classic", "waterfox-classic", "/usr/bin/waterfox-classic"),
-                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox 3rd Generation", "waterfox-g3", "/usr/bin/waterfox-g3"),
-                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox 4th Generation", "waterfox-g4", "/usr/bin/waterfox-g4"),
-                Browser(BROWSER_TYPE_FIREFOX,  "Floorp", "floorp", "/usr/bin/floorp"),
+                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox", "waterfox", "@PREFIX@/bin/waterfox"),
+                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox Current", "waterfox-current", "@PREFIX@/bin/waterfox-current"),
+                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox Classic", "waterfox-classic", "@PREFIX@/bin/waterfox-classic"),
+                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox 3rd Generation", "waterfox-g3", "@PREFIX@/bin/waterfox-g3"),
+                Browser(BROWSER_TYPE_FIREFOX,  "Waterfox 4th Generation", "waterfox-g4", "@PREFIX@/bin/waterfox-g4"),
+                Browser(BROWSER_TYPE_FIREFOX,  "Floorp", "floorp", "@PREFIX@/bin/floorp"),
                 Browser(BROWSER_TYPE_WATERFOX_FLATPAK, "Waterfox (Flatpak)", "/var/lib/flatpak/exports/bin/net.waterfox.waterfox", "/var/lib/flatpak/exports/bin/net.waterfox.waterfox"),
                 Browser(BROWSER_TYPE_WATERFOX_FLATPAK, "Waterfox (Flatpak)", ".local/share/flatpak/exports/bin/net.waterfox.waterfox", ".local/share/flatpak/exports/bin/net.waterfox.waterfox"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Vivaldi", "vivaldi-stable", "/usr/bin/vivaldi-stable"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Vivaldi Snapshot", "vivaldi-snapshot", "/usr/bin/vivaldi-snapshot"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Vivaldi", "vivaldi-stable", "@PREFIX@/bin/vivaldi-stable"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Vivaldi Snapshot", "vivaldi-snapshot", "@PREFIX@/bin/vivaldi-snapshot"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Vivaldi (Flatpak)", "/var/lib/flatpak/exports/bin/com.vivaldi.Vivaldi", "/var/lib/flatpak/exports/bin/com.vivaldi.Vivaldi"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Vivaldi (Flatpak)", ".local/share/flatpak/exports/bin/com.vivaldi.Vivaldi", ".local/share/flatpak/exports/bin/com.vivaldi.Vivaldi"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Microsoft Edge", "microsoft-edge-stable", "/usr/bin/microsoft-edge-stable"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Microsoft Edge Beta", "microsoft-edge-beta", "/usr/bin/microsoft-edge-beta"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Microsoft Edge Dev", "microsoft-edge-dev", "/usr/bin/microsoft-edge-dev"),
-                Browser(BROWSER_TYPE_CHROMIUM, "FlashPeak Slimjet", "flashpeak-slimjet", "/usr/bin/flashpeak-slimjet"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Microsoft Edge", "microsoft-edge-stable", "@PREFIX@/bin/microsoft-edge-stable"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Microsoft Edge Beta", "microsoft-edge-beta", "@PREFIX@/bin/microsoft-edge-beta"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Microsoft Edge Dev", "microsoft-edge-dev", "@PREFIX@/bin/microsoft-edge-dev"),
+                Browser(BROWSER_TYPE_CHROMIUM, "FlashPeak Slimjet", "flashpeak-slimjet", "@PREFIX@/bin/flashpeak-slimjet"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Ungoogled Chromium (Flatpak)", "/var/lib/flatpak/exports/bin/io.github.ungoogled_software.ungoogled_chromium", "/var/lib/flatpak/exports/bin/io.github.ungoogled_software.ungoogled_chromium"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Ungoogled Chromium (Flatpak)", ".local/share/flatpak/exports/bin/io.github.ungoogled_software.ungoogled_chromium", ".local/share/flatpak/exports/bin/io.github.ungoogled_software.ungoogled_chromium"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Chromium (Flatpak)", "/var/lib/flatpak/exports/bin/org.chromium.Chromium", "/var/lib/flatpak/exports/bin/org.chromium.Chromium"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Chromium (Flatpak)", ".local/share/flatpak/exports/bin/org.chromium.Chromium", ".local/share/flatpak/exports/bin/org.chromium.Chromium"),
-                Browser(BROWSER_TYPE_FALKON, "Falkon", "falkon", "/usr/bin/falkon"),
+                Browser(BROWSER_TYPE_FALKON, "Falkon", "falkon", "@PREFIX@/bin/falkon"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Edge (Flatpak)", "/var/lib/flatpak/exports/bin/com.microsoft.Edge", "/var/lib/flatpak/exports/bin/com.microsoft.Edge"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Edge (Flatpak)", ".local/share/flatpak/exports/bin/com.microsoft.Edge", ".local/share/flatpak/exports/bin/com.microsoft.Edge"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Brave (Flatpak)", "/var/lib/flatpak/exports/bin/com.brave.Browser", "/var/lib/flatpak/exports/bin/com.brave.Browser"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Brave (Flatpak)", ".local/share/flatpak/exports/bin/com.brave.Browser", ".local/share/flatpak/exports/bin/com.brave.Browser"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Yandex", "yandex-browser", "/usr/bin/yandex-browser"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Yandex", "yandex-browser", "@PREFIX@/bin/yandex-browser"),
                 Browser(BROWSER_TYPE_FALKON, "Falkon (Flatpak)", "/var/lib/flatpak/exports/bin/org.kde.falkon", "/var/lib/flatpak/exports/bin/org.kde.falkon"),
                 Browser(BROWSER_TYPE_FALKON, "Falkon (Flatpak)", ".local/share/flatpak/exports/bin/org.kde.falkon", ".local/share/flatpak/exports/bin/org.kde.falkon"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Naver Whale", "naver-whale-stable", "/usr/bin/naver-whale-stable"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Naver Whale", "naver-whale-stable", "@PREFIX@/bin/naver-whale-stable"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Yandex (Flatpak)", "/var/lib/flatpak/exports/bin/ru.yandex.Browser", "/var/lib/flatpak/exports/bin/ru.yandex.Browser"),
                 Browser(BROWSER_TYPE_CHROMIUM, "Yandex (Flatpak)", ".local/share/flatpak/exports/bin/ru.yandex.Browser", ".local/share/flatpak/exports/bin/ru.yandex.Browser"),
-                Browser(BROWSER_TYPE_CHROMIUM, "Thorium", "thorium-browser", "/usr/bin/thorium-browser"),
-                Browser(BROWSER_TYPE_FIREFOX, "Floorp", "floorp", "/usr/bin/floorp"),
+                Browser(BROWSER_TYPE_CHROMIUM, "Thorium", "thorium-browser", "@PREFIX@/bin/thorium-browser"),
+                Browser(BROWSER_TYPE_FIREFOX, "Floorp", "floorp", "@PREFIX@/bin/floorp"),
                 Browser(BROWSER_TYPE_FLOORP_FLATPAK, "Floorp (Flatpak)", "/var/lib/flatpak/exports/bin/one.ablaze.floorp", "/var/lib/flatpak/exports/bin/one.ablaze.floorp"),
                 Browser(BROWSER_TYPE_FLOORP_FLATPAK, "Floorp (Flatpak)", ".local/share/flatpak/exports/bin/one.ablaze.floorp", ".local/share/flatpak/exports/bin/one.ablaze.floorp")
                 ]
@@ -271,9 +306,11 @@
         shutil.rmtree(os.path.join(FALKON_PROFILES_DIR, webapp.codename), ignore_errors=True)
 
     def create_webapp(self, name, desc, url, icon, category, browser, custom_parameters, isolate_profile=True, navbar=False, privatewindow=False):
+        if browser.browser_type == BROWSER_TYPE_EMBER:
+            isolate_profile = True
         # Generate a 4 digit random code (to prevent name collisions, so we can define multiple launchers with the same name)
         random_code =  ''.join(choice(string.digits) for _ in range(4))
-        codename = "".join(filter(str.isalpha, name)) + random_code
+        codename = secrets.token_hex(12) if browser.browser_type == BROWSER_TYPE_EMBER else "".join(filter(str.isalpha, name)) + random_code
         path = os.path.join(APPS_DIR, "WebApp-%s.desktop" % codename)
 
         if not desc:
@@ -282,11 +319,11 @@
         with open(path, 'w') as desktop_file:
             desktop_file.write("[Desktop Entry]\n")
             desktop_file.write("Version=1.0\n")
-            desktop_file.write("Name=%s\n" % name)
-            desktop_file.write("Comment=%s\n" % desc)
+            desktop_file.write("Name=%s\n" % desktop_string(name))
+            desktop_file.write("Comment=%s\n" % desktop_string(desc))
 
             exec_string = self.get_exec_string(browser, codename, custom_parameters, icon, isolate_profile, navbar,
-                                               privatewindow, url)
+                                               privatewindow, url, name)
 
             desktop_file.write("Exec=%s\n" % exec_string)
             desktop_file.write("Terminal=false\n")
@@ -324,7 +361,18 @@
                 os.symlink(falkon_profile_path, falkon_orig_prof_dir)
 
 
-    def get_exec_string(self, browser, codename, custom_parameters, icon, isolate_profile, navbar, privatewindow, url):
+    def get_exec_string(self, browser, codename, custom_parameters, icon, isolate_profile, navbar, privatewindow, url, name):
+        if browser.browser_type == BROWSER_TYPE_EMBER:
+            # Desktop Entry Exec quoting is not shell quoting. Percent is a
+            # field-code introducer and must be escaped even inside quotes.
+            def desktop_arg(value):
+                quoted = value.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
+                return desktop_string('"' + quoted + '"')
+            args = [browser.exec_path, "--webapp-id=" + codename,
+                    "--webapp-url=" + url, "--webapp-name=" + name]
+            if privatewindow:
+                args.append("--webapp-private")
+            return " ".join(desktop_arg(arg) for arg in args)
         if browser.browser_type in [BROWSER_TYPE_FIREFOX, BROWSER_TYPE_FIREFOX_FLATPAK, BROWSER_TYPE_FIREFOX_SNAP, BROWSER_TYPE_ZEN_FLATPAK]:
             # Firefox based
             if browser.browser_type == BROWSER_TYPE_FIREFOX:
@@ -347,9 +395,9 @@
                 exec_string += " {}".format(custom_parameters)
             exec_string += " \"" + url + "\"" + "'"
             # Create a Firefox profile
-            shutil.copytree('/usr/share/webapp-manager/firefox/profile', firefox_profile_path, dirs_exist_ok = True)
+            shutil.copytree('@PREFIX@/share/webapp-manager/firefox/profile', firefox_profile_path, dirs_exist_ok = True)
             if navbar:
-                shutil.copy('/usr/share/webapp-manager/firefox/userChrome-with-navbar.css',
+                shutil.copy('@PREFIX@/share/webapp-manager/firefox/userChrome-with-navbar.css',
                             os.path.join(firefox_profile_path, "chrome", "userChrome.css"))
         elif browser.browser_type == BROWSER_TYPE_LIBREWOLF_FLATPAK:
             # LibreWolf flatpak
@@ -366,9 +414,9 @@
                 exec_string += " {}".format(custom_parameters)
             exec_string += " \"" + url + "\"" + "'"
             # Create a Firefox profile
-            shutil.copytree('/usr/share/webapp-manager/firefox/profile', firefox_profile_path, dirs_exist_ok = True)
+            shutil.copytree('@PREFIX@/share/webapp-manager/firefox/profile', firefox_profile_path, dirs_exist_ok = True)
             if navbar:
-                shutil.copy('/usr/share/webapp-manager/firefox/userChrome-with-navbar.css',
+                shutil.copy('@PREFIX@/share/webapp-manager/firefox/userChrome-with-navbar.css',
                             os.path.join(firefox_profile_path, "chrome", "userChrome.css"))
         elif browser.browser_type == BROWSER_TYPE_FLOORP_FLATPAK:
             # Floorp flatpak
@@ -385,9 +433,9 @@
                 exec_string += " {}".format(custom_parameters)
             exec_string += " \"" + url + "\"" + "'"
             # Create a Firefox profile
-            shutil.copytree('/usr/share/webapp-manager/firefox/profile', firefox_profile_path, dirs_exist_ok = True)
+            shutil.copytree('@PREFIX@/share/webapp-manager/firefox/profile', firefox_profile_path, dirs_exist_ok = True)
             if navbar:
-                shutil.copy('/usr/share/webapp-manager/firefox/userChrome-with-navbar.css',
+                shutil.copy('@PREFIX@/share/webapp-manager/firefox/userChrome-with-navbar.css',
                             os.path.join(firefox_profile_path, "chrome", "userChrome.css"))
         elif browser.browser_type == BROWSER_TYPE_EPIPHANY:
             # Epiphany based
@@ -444,22 +492,24 @@
         return exec_string
 
     def edit_webapp(self, path, name, desc, browser, url, icon, category, custom_parameters, codename, isolate_profile, navbar, privatewindow):
+        if browser.browser_type == BROWSER_TYPE_EMBER:
+            isolate_profile = True
         if not desc:
             desc = _("Web App")
 
         config = configparser.RawConfigParser()
         config.optionxform = str
         config.read(path)
-        config.set("Desktop Entry", "Name", name)
+        config.set("Desktop Entry", "Name", desktop_string(name))
         config.set("Desktop Entry", "Icon", icon)
-        config.set("Desktop Entry", "Comment", desc)
+        config.set("Desktop Entry", "Comment", desktop_string(desc))
         config.set("Desktop Entry", "Categories", "GTK;%s;" % category)
 
         try:
             # This will raise an exception on legacy apps which
             # have no X-WebApp-URL and X-WebApp-Browser
 
-            exec_line = self.get_exec_string(browser, codename, custom_parameters, icon, isolate_profile, navbar, privatewindow, url)
+            exec_line = self.get_exec_string(browser, codename, custom_parameters, icon, isolate_profile, navbar, privatewindow, url, name)
 
             config.set("Desktop Entry", "Exec", exec_line)
             config.set("Desktop Entry", "X-WebApp-Browser", browser.name)
