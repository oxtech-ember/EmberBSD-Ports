$NetBSD$

The Wayland profile stubs the GTK3 decoration stack; the core
library drops the gtk/gtk.h include and defines a local GtkBorder
with the same four-gint layout for the remaining references.

--- src/meta/common.h.orig
+++ src/meta/common.h
@@ -29,7 +29,16 @@
 #include <X11/extensions/XInput.h>
 #include <X11/extensions/XInput2.h>
 #include <glib.h>
-#include <gtk/gtk.h>
+/* EmberBSD Wayland profile: the GTK3 server-side decoration stack is
+ * stubbed (ui/); no GTK header enters the core library. GtkBorder
+ * keeps its upstream four-gint layout for the remaining references. */
+typedef struct _GtkBorder
+{
+  gint left;
+  gint right;
+  gint top;
+  gint bottom;
+} GtkBorder;
 
 #include "clutter/clutter.h"
 
