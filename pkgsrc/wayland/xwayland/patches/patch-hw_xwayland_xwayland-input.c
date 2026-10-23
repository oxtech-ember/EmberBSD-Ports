$NetBSD$

Origin: EmberBSD (AI-assisted).
Format uint32_t seat and tablet button identifiers with PRIu32.
Keep message text, control flow, and protocol handling unchanged.

--- hw/xwayland/xwayland-input.c.orig
+++ hw/xwayland/xwayland-input.c
@@ -24,6 +24,7 @@
  * SOFTWARE.
  */
 
+#include <inttypes.h>
 #include <math.h>
 #include <xwayland-config.h>
 
@@ -1683,7 +1684,7 @@
 
     if (type_atom == None)
         type_atom = MakeAtom(driver, strlen(driver), TRUE);
-    snprintf(name, sizeof name, "%s:%d", driver, xwl_seat->id);
+    snprintf(name, sizeof name, "%s:%" PRIu32, driver, xwl_seat->id);
     AssignTypeAndName(dev, type_atom, name);
     dev->public.devicePrivate = xwl_seat;
     dev->type = SLAVE;
@@ -2378,7 +2379,7 @@
     }
 
     if (!xbtn) {
-        ErrorF("unknown tablet button number %d\n", button);
+        ErrorF("unknown tablet button number %" PRIu32 "\n", button);
         return;
     }
 
