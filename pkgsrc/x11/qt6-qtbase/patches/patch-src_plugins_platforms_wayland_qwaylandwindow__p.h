$NetBSD$

Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

State for the opt-in immediate-update mode; see
patch-src_plugins_platforms_wayland_qwaylandwindow.cpp. The member is
appended at the end of the class to keep the layout of the other members.

--- src/plugins/platforms/wayland/qwaylandwindow_p.h.orig
+++ src/plugins/platforms/wayland/qwaylandwindow_p.h
@@ -415,6 +415,13 @@
     static QWaylandWindow *mMouseGrab;
     static QWaylandWindow *mTopPopup;
 
+    // Deliver update requests at once instead of after the pending frame
+    // callback. Low-latency video windows opt in before QWindow::create()
+    // with the QObject dynamic property _q_waylandImmediateUpdates, or
+    // globally with QT_WAYLAND_IMMEDIATE_UPDATES=1. Written once in the
+    // constructor, read from the render thread.
+    bool mImmediateUpdates = false;
+
     friend class QWaylandSubSurface;
 };
 
