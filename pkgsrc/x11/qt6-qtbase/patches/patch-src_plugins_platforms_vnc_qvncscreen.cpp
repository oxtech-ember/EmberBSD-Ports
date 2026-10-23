$NetBSD$

Origin: AI-assisted EmberBSD adaptation for Qt 6.12.0, not submitted upstream.

Initialize the VNC screen once, from QVncIntegration::initialize().
The constructor previously allocated a dirty map that the integration replaced.
Release the final owned dirty map, tile array and comparison buffer on teardown.

--- src/plugins/platforms/vnc/qvncscreen.cpp.orig
+++ src/plugins/platforms/vnc/qvncscreen.cpp
@@ -19,7 +19,6 @@
 QVncScreen::QVncScreen(const QStringList &args)
     : mArgs(args)
 {
-    initialize();
 }
 
 QVncScreen::~QVncScreen()
@@ -28,6 +27,7 @@
     if (clientCursor)
         delete clientCursor;
 #endif
+    delete dirty;
 }
 
 bool QVncScreen::initialize()
