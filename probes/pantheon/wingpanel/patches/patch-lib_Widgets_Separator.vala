$NetBSD$

EmberBSD GTK4 port: GtkSeparator cannot be subclassed in GTK4 (private
instance struct); the deprecated wrapper becomes a thin Gtk.Box that
mimics the horizontal separator line. Origin: EmberBSD (AI-assisted).

--- lib/Widgets/Separator.vala.orig	2026-10-14 21:07:31.134062694 +0300
+++ lib/Widgets/Separator.vala	2026-10-14 21:07:31.081361144 +0300
@@ -1,29 +1,26 @@
 /*
- * Copyright (c) 2011-2017 elementary LLC (https://elementary.io)
- *
- * This program is free software; you can redistribute it and/or
- * modify it under the terms of the GNU General Public
- * License as published by the Free Software Foundation; either
- * version 2 of the License, or (at your option) any later version.
- *
- * This program is distributed in the hope that it will be useful,
- * but WITHOUT ANY WARRANTY; without even the implied warranty of
- * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
- * General Public License for more details.
- *
- * You should have received a copy of the GNU General Public
- * License along with this program; if not, write to the
- * Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
- * Boston, MA 02110-1301 USA.
+ * SPDX-License-Identifier: GPL-2-or-later
+ * SPDX-FileCopyrightText: 2011-2017 Wingpanel Developers (http://launchpad.net/wingpanel)
+ * SPDX-FileCopyrightText: 2026 elementary, Inc. (https://elementary.io)
+ */
+
+/*
+ * EmberBSD GTK4 port: GtkSeparator cannot be subclassed in GTK4 (private
+ * instance struct), so the deprecated wrapper becomes a thin Gtk.Box that
+ * mimics the horizontal separator line. Origin: EmberBSD (AI-assisted).
  */
 
 [Version (deprecated = true, deprecated_since = "3.0.0", replacement = "Gtk.Separator")]
-public class Wingpanel.Widgets.Separator : Gtk.Separator {
+public class Wingpanel.Widgets.Separator : Gtk.Box {
     public Separator () {
         Object (
             margin_bottom: 3,
             margin_top: 3,
-            orientation: Gtk.Orientation.HORIZONTAL
+            orientation: Gtk.Orientation.HORIZONTAL,
+            spacing: 0
         );
+
+        height_request = 1;
+        add_css_class ("separator");
     }
 }
