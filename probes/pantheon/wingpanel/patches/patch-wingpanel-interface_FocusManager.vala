$NetBSD$

EmberBSD GTK4 port: mutter 49 changed Meta.Window.begin_grab_op to
(grabop, sprite, timestamp, point); route the mutter-49 call through a
new HAS_MUTTER49 branch. Origin: EmberBSD (AI-assisted).

--- wingpanel-interface/FocusManager.vala	2025-12-03 19:15:29.000000000 +0300
+++ FocusManager.vala	2026-10-14 21:03:50.638771424 +0300
@@ -134,7 +134,14 @@
                         return Clutter.EVENT_PROPAGATE;
                     }
 
-#if HAS_MUTTER46
+#if HAS_MUTTER49
+                    window.begin_grab_op (
+                        Meta.GrabOp.MOVING,
+                        null,
+                        event.get_time (),
+                        { x, y }
+                    );
+#elif HAS_MUTTER46
                     window.begin_grab_op (
                         Meta.GrabOp.MOVING,
                         event.get_device (),
