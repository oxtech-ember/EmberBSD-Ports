$NetBSD$

Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

Add an opt-in immediate-update mode for low-latency windows. By default a
window waits for the pending wl_surface.frame callback before Qt delivers
the next update request, so a video frame that arrives after the
compositor started its cycle is shown one refresh period late. A window
with the QObject dynamic property _q_waylandImmediateUpdates (or the
environment variable QT_WAYLAND_IMMEDIATE_UPDATES=1) renders and commits
as soon as it is updated; the compositor may show the newest buffer. The
property is read once when the platform window is created, so set it
before QWindow::create() or show(). It is not a QWaylandWindow::property()
entry. After the frame callback timed out the normal gate applies again,
so a hidden or unexposed surface does not spin.

--- src/plugins/platforms/wayland/qwaylandwindow.cpp.orig
+++ src/plugins/platforms/wayland/qwaylandwindow.cpp
@@ -66,6 +66,13 @@
         if (ok)
             mFrameCallbackTimeout = frameCallbackTimeout;
     }
+    {
+        const QVariant immediate = window->property("_q_waylandImmediateUpdates");
+        if (immediate.isValid())
+            mImmediateUpdates = immediate.toBool();
+        else
+            mImmediateUpdates = qEnvironmentVariableIntValue("QT_WAYLAND_IMMEDIATE_UPDATES") > 0;
+    }
 
     mSurfaceFormat.setColorSpace(QColorSpace{});
     initializeWlSurface();
@@ -1764,8 +1771,11 @@
     qCDebug(lcWaylandBackingstore) << "requestUpdate";
     Q_ASSERT(hasPendingUpdateRequest()); // should be set by QPA
 
-    // If we have a frame callback all is good and will be taken care of there
-    {
+    // If we have a frame callback all is good and will be taken care of there.
+    // An immediate-update window does not wait for it: the compositor may
+    // show the newest committed buffer. The gate stays in force after the
+    // frame callback timed out, so a hidden surface cannot spin.
+    if (!mImmediateUpdates || mFrameCallbackTimedOut) {
         QMutexLocker locker(&mFrameSyncMutex);
         if (mFrameCallback)
             return;
@@ -1775,7 +1785,7 @@
     // so use invokeMethod to delay the delivery a bit.
     QMetaObject::invokeMethod(this, [this] {
         // Things might have changed in the meantime
-        {
+        if (!mImmediateUpdates || mFrameCallbackTimedOut) {
             QMutexLocker locker(&mFrameSyncMutex);
             if (mFrameCallback)
                 return;
